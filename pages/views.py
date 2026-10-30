"""Static page views."""

from django.shortcuts import render

from catalog.selectors import attach_prices, storefront_products

POPULAR_COUNT = 4


def home(request):
    """Home page: hero, how it works, popular products from the catalog."""
    popular = storefront_products().order_by("-popularity", "sort_order", "id")[:POPULAR_COUNT]
    return render(request, "pages/home.html", {"products": attach_prices(popular)})
