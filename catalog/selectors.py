"""Read-side helpers for the storefront (queries + price attachment)."""

from datetime import datetime

from django.utils import timezone

from catalog.models import Product
from catalog.pricing import get_price


def storefront_products():
    """Published products with images prefetched (cover costs no extra queries)."""
    return Product.objects.published().with_images()


def attach_prices(products, now: datetime | None = None):
    """Set ``product.price`` on every product. Campaign and preorders are loaded once."""
    now = now or timezone.now()
    products = list(products)
    if not products:
        return products
    from promo.models import DiscountCampaign, PreorderRelease

    releases = {
        row.product_id: row
        for row in PreorderRelease.objects.filter(product_id__in=[item.pk for item in products])
    }
    campaign = (
        DiscountCampaign.objects.filter(is_active=True, starts_at__lte=now, ends_at__gt=now)
        .order_by("-percent")
        .first()
    )
    for product in products:
        product.price = get_price(
            product, now, release=releases.get(product.pk), campaign=campaign, _lookup=False
        )
    return products


def catalog_counts() -> dict[str, int]:
    """Numbers for the tabs: all published / published combos."""
    published = Product.objects.published()
    return {"all": published.count(), "combo": published.filter(is_combo=True).count()}
