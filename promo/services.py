"""Open and close the sales window, then mail the PDF when it is uploaded."""

from django.utils import timezone

from delivery.services import issue_paid_order
from orders.models import Order
from promo.models import PreorderRelease


def tick_preorders(now=None) -> dict:
    now = now or timezone.now()
    opened = PreorderRelease.objects.filter(
        status=PreorderRelease.Status.SCHEDULED, sales_start__lte=now
    ).update(status=PreorderRelease.Status.SELLING)
    closed = PreorderRelease.objects.filter(
        status=PreorderRelease.Status.SELLING, sales_end__lt=now
    ).update(status=PreorderRelease.Status.CLOSED)
    released = 0
    failed = 0
    due = PreorderRelease.objects.filter(
        status__in=(PreorderRelease.Status.SELLING, PreorderRelease.Status.CLOSED),
        release_date__lte=now,
    ).select_related("product")
    for release in due:
        if release.product.pdf_file or _combo_ready(release.product):
            release_preorder(release.pk, now=now)
            released += 1
        else:
            release.status = PreorderRelease.Status.FAILED
            release.save(update_fields=["status"])
            failed += 1
    return {"opened": opened, "closed": closed, "released": released, "failed": failed}


def _combo_ready(product) -> bool:
    from catalog.files import source_pdfs

    return bool(source_pdfs(product))


def release_preorder(release_id, now=None) -> int:
    """Send files for every order still waiting. Safe to run twice."""
    now = now or timezone.now()
    release = PreorderRelease.objects.select_related("product").get(pk=release_id)
    if not _combo_ready(release.product):
        release.status = PreorderRelease.Status.FAILED
        release.save(update_fields=["status"])
        return 0
    waiting = (
        Order.objects.filter(status=Order.Status.AWAITING_RELEASE, items__product=release.product)
        .distinct()
        .order_by("created_at")
    )
    sent = 0
    for order in waiting.iterator(chunk_size=50):
        issue_paid_order(order.pk)
        sent += 1
    release.status = PreorderRelease.Status.RELEASED
    release.released_at = now
    release.save(update_fields=["status", "released_at"])
    return sent
