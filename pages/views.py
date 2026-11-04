"""Static page views."""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from catalog.selectors import attach_prices, storefront_products
from pages.models import Page

POPULAR_COUNT = 4


def home(request):
    """Home page: hero, how it works, popular products from the catalog."""
    popular = storefront_products().order_by("-popularity", "sort_order", "id")[:POPULAR_COUNT]
    about = Page.objects.filter(slug=Page.Slug.ABOUT, is_published=True).first()
    return render(request, "pages/home.html", {"products": attach_prices(popular), "about": about})


def page(request, slug):
    text = get_object_or_404(Page, slug=slug, is_published=True)
    return render(request, "pages/page.html", {"page": text})


def robots(_request):
    admin = settings.ADMIN_URL.strip("/")
    lines = [
        "User-agent: *",
        "Disallow: /cart/",
        "Disallow: /d/",
        f"Disallow: /{admin}/",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
