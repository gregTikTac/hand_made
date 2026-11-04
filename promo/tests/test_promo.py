"""Campaigns, preorders and combo files."""

from datetime import timedelta
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone
from pypdf import PdfWriter

from catalog.factories import ProductFactory
from catalog.models import ComboItem
from catalog.pricing import get_price
from delivery.models import DownloadLink
from delivery.services import issue_paid_order
from orders.services import place_order, transition
from promo.models import DiscountCampaign, PreorderRelease
from promo.services import release_preorder, tick_preorders

pytestmark = pytest.mark.django_db


def pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_campaign_price_is_the_one_in_the_order():
    product = ProductFactory(base_price=60000)
    now = timezone.now()
    campaign = DiscountCampaign.objects.create(
        title="Весна",
        percent=30,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(days=2),
    )
    info = get_price(product)
    assert info.final == 42000
    assert info.campaign_id == campaign.pk
    order = place_order(
        products=[product],
        seen={product.pk: info.final},
        email="a@example.com",
        marketing=False,
        ip=None,
        user_agent="",
    )
    assert order.items.get().campaign_id == campaign.pk
    assert order.total == 42000


def test_overlapping_campaigns_are_rejected():
    now = timezone.now()
    DiscountCampaign.objects.create(
        title="Первая",
        percent=10,
        starts_at=now,
        ends_at=now + timedelta(days=3),
    )
    second = DiscountCampaign(
        title="Вторая",
        percent=20,
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=4),
    )
    with pytest.raises(ValidationError):
        second.full_clean()


def test_preorder_opens_and_larger_discount_wins():
    now = timezone.now()
    product = ProductFactory(base_price=60000)
    PreorderRelease.objects.create(
        product=product,
        sales_start=now - timedelta(minutes=5),
        sales_end=now + timedelta(days=2),
        release_date=now + timedelta(days=10),
        discount_percent=20,
        status=PreorderRelease.Status.SCHEDULED,
    )
    DiscountCampaign.objects.create(
        title="Большая",
        percent=30,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(days=1),
    )
    tick_preorders(now)
    product.preorder.refresh_from_db()
    assert product.preorder.status == PreorderRelease.Status.SELLING
    info = get_price(product, now)
    assert info.final == 42000
    assert info.is_preorder and info.is_sale


def test_combo_sends_each_toys_pdf():
    fox = ProductFactory(title="Лиса")
    goat = ProductFactory(title="Коза")
    for toy in (fox, goat):
        toy.pdf_file.save("toy.pdf", ContentFile(pdf_bytes()), save=True)
    combo = ProductFactory(title="Двое", is_combo=True, pdf_file=None, status="draft")
    combo.status = "published"
    combo.save()
    ComboItem.objects.create(combo=combo, item=fox, position=1)
    ComboItem.objects.create(combo=combo, item=goat, position=2)
    order = place_order(
        products=[combo],
        seen={combo.pk: get_price(combo).final},
        email="buyer@example.com",
        marketing=False,
        ip=None,
        user_agent="",
    )
    transition(order, "pay")
    transition(order, "succeeded")
    issue_paid_order(order.pk)
    labels = set(DownloadLink.objects.values_list("label", flat=True))
    assert labels == {"Лиса", "Коза"}


def test_release_sends_the_waiting_order():
    now = timezone.now()
    product = ProductFactory(pdf_file=None, status="draft")
    release = PreorderRelease.objects.create(
        product=product,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=1),
        release_date=now - timedelta(minutes=1),
        discount_percent=0,
        status=PreorderRelease.Status.SELLING,
    )
    order = place_order(
        products=[product],
        seen={product.pk: get_price(product).final},
        email="buyer@example.com",
        marketing=False,
        ip=None,
        user_agent="",
    )
    transition(order, "pay")
    transition(order, "succeeded")
    issue_paid_order(order.pk)
    order.refresh_from_db()
    assert order.status == "awaiting_release"
    product.pdf_file.save("ready.pdf", ContentFile(pdf_bytes()), save=True)
    assert release_preorder(release.pk) == 1
    order.refresh_from_db()
    assert order.status == "fulfilled"
    assert DownloadLink.objects.filter(order_item__order=order).count() == 1
