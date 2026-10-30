"""Read-side helpers for the storefront (queries + price attachment)."""

from datetime import datetime

from django.utils import timezone

from catalog.models import Product
from catalog.pricing import get_price


def storefront_products():
    """Published products with images prefetched (cover costs no extra queries)."""
    return Product.objects.published().with_images()


def attach_prices(products, now: datetime | None = None):
    """Set ``product.price`` (a PriceInfo) on every product — the only price shown to customers."""
    now = now or timezone.now()
    products = list(products)
    for product in products:
        product.price = get_price(product, now)
    return products


def catalog_counts() -> dict[str, int]:
    """Numbers for the tabs: all published / published combos."""
    published = Product.objects.published()
    return {"all": published.count(), "combo": published.filter(is_combo=True).count()}
