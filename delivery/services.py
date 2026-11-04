"""Create watermarked copies, limited links, and the letter. Tokens stay in the letter only."""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from catalog.files import source_pdfs
from delivery.models import LINK_DAYS, LINK_DOWNLOADS, DownloadLink, EmailLog
from delivery.watermark import stamp_pdf
from orders.models import Order
from orders.services import transition

SENDABLE = (Order.Status.PAID, Order.Status.FULFILLED, Order.Status.AWAITING_RELEASE)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _absolute(token: str) -> str:
    root = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    return root + reverse("delivery:download", args=[token])


def _create_links(order) -> list[dict]:
    """Make a fresh link for every file. Caller decides when old links are revoked."""
    prepared = []
    for item in order.items.select_related("product"):
        for label, stored in source_pdfs(item.product):
            with stored.open("rb") as handle:
                stamped = stamp_pdf(handle.read(), f"Куплено: {order.email}, заказ {order.number}")
            token = secrets.token_urlsafe(32)
            link = DownloadLink(
                order_item=item,
                label=label[:200],
                token_hash=hash_token(token),
                expires_at=timezone.now() + timedelta(days=LINK_DAYS),
                max_downloads=LINK_DOWNLOADS,
            )
            link.watermarked.save(f"{token[:16]}.pdf", ContentFile(stamped), save=False)
            link.save()
            prepared.append({"label": link.label, "url": _absolute(token)})
    return prepared


def _send(order, template: str, dedup_key: str, links: list[dict], *, release_date=None) -> bool:
    """Send once per ``dedup_key``. Returns True when a new letter went out."""
    log, created = EmailLog.objects.get_or_create(
        dedup_key=dedup_key,
        defaults={
            "order": order,
            "to": order.email,
            "template": template,
            "status": EmailLog.Status.QUEUED,
        },
    )
    if not created and log.status == EmailLog.Status.SENT:
        return False
    context = {
        "order": order,
        "links": links,
        "site_name": settings.SITE_NAME,
        "release_date": release_date,
        "days": LINK_DAYS,
        "downloads": LINK_DOWNLOADS,
    }
    subject = {
        "order_paid": f"Ваш мастер-класс — заказ {order.number}",
        "preorder_paid": f"Предзаказ принят — {order.number}",
        "preorder_released": f"Файл предзаказа готов — {order.number}",
        "resend_links": f"Ссылки на файлы ещё раз — {order.number}",
    }[template]
    text = render_to_string(f"delivery/email/{template}.txt", context)
    html = render_to_string(f"delivery/email/{template}.html", context)
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [order.email])
    message.attach_alternative(html, "text/html")
    log.attempts += 1
    try:
        message.send(fail_silently=False)
    except Exception as exc:
        log.status = EmailLog.Status.FAILED
        log.error = str(exc)[:2000]
        log.save(update_fields=["attempts", "status", "error"])
        raise
    log.status = EmailLog.Status.SENT
    log.error = ""
    log.save(update_fields=["attempts", "status", "error"])
    return True


def _finish_status(order, *, missing: bool):
    if order.status == Order.Status.FULFILLED:
        return order
    if missing and order.status == Order.Status.PAID:
        return transition(order, "preorder")
    if not missing and order.status in (Order.Status.PAID, Order.Status.AWAITING_RELEASE):
        return transition(order, "files_sent" if order.status == Order.Status.PAID else "release")
    return order


@transaction.atomic
def issue_paid_order(order_id) -> Order:
    """After a successful payment: links for files we already have, or a preorder hold."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status not in (Order.Status.PAID, Order.Status.AWAITING_RELEASE):
        return order
    if order.emails.filter(dedup_key=f"receipt:{order.pk}", status=EmailLog.Status.SENT).exists():
        return order

    missing = any(not source_pdfs(item.product) for item in order.items.select_related("product"))
    has_files = any(source_pdfs(item.product) for item in order.items.select_related("product"))
    if not has_files:
        _send(order, "preorder_paid", f"preorder:{order.pk}", [], release_date=_release_date(order))
        return _finish_status(order, missing=True)

    DownloadLink.objects.filter(order_item__order=order, revoked=False).update(revoked=True)
    links = _create_links(order)
    template = (
        "preorder_released" if order.status == Order.Status.AWAITING_RELEASE else "order_paid"
    )
    key = (
        f"release-wait:{order.pk}"
        if order.status == Order.Status.AWAITING_RELEASE
        else f"receipt:{order.pk}"
    )
    _send(order, template, key, links, release_date=_release_date(order))
    return _finish_status(order, missing=missing)


def _release_date(order):
    from promo.models import PreorderRelease

    release = (
        PreorderRelease.objects.filter(product__order_items__order=order)
        .order_by("release_date")
        .first()
    )
    return release.release_date if release else None


@transaction.atomic
def resend_order(order_id) -> bool:
    """New links to the same address. The previous links stop working."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status not in SENDABLE:
        return False
    if not any(source_pdfs(item.product) for item in order.items.select_related("product")):
        return False
    DownloadLink.objects.filter(order_item__order=order, revoked=False).update(revoked=True)
    links = _create_links(order)
    if not links:
        return False
    count = order.emails.filter(template="resend_links").count() + 1
    _send(order, "resend_links", f"resend:{order.pk}:{count}", links)
    _finish_status(order, missing=False)
    return True


def resend_to_email(email: str) -> None:
    """Same reply whether or not this address has an order."""
    orders = Order.objects.filter(email__iexact=email.strip(), status__in=SENDABLE)
    for order in orders:
        resend_order(order.pk)
