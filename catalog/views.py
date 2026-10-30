"""Storefront views: catalog (all / combo, 'show more' via HTMX) and product page."""

from django.core.paginator import InvalidPage, Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from django.views.decorators.vary import vary_on_headers

from catalog.models import Product
from catalog.selectors import attach_prices, catalog_counts, storefront_products

PAGE_SIZE = 12  # even: the grid is always 2 per row on mobile


def _catalog_page(request, *, combo_only: bool):
    queryset = storefront_products()
    if combo_only:
        queryset = queryset.combos()
    paginator = Paginator(queryset, PAGE_SIZE)
    try:
        page = paginator.page(request.GET.get("page") or 1)
    except InvalidPage:
        raise Http404("Страница каталога не найдена") from None

    context = {
        "page": page,
        "products": attach_prices(page.object_list),
        "combo_only": combo_only,
        "counts": catalog_counts(),
        "next_url": f"{request.path}?page={page.next_page_number()}" if page.has_next() else None,
    }
    template = (
        "catalog/_grid_more.html" if request.headers.get("HX-Request") else "catalog/list.html"
    )
    return render(request, template, context)


@require_GET
@vary_on_headers("HX-Request")
def catalog_all(request):
    return _catalog_page(request, combo_only=False)


@require_GET
@vary_on_headers("HX-Request")
def catalog_combo(request):
    return _catalog_page(request, combo_only=True)


@require_GET
def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.prefetch_related("images", "videos").filter(slug=slug)
    )
    is_preview = not product.is_published
    if is_preview and not request.user.is_staff:
        raise Http404("Мастер-класс не найден")

    (product,) = attach_prices([product])
    images = sorted(
        product.images.all(), key=lambda image: (not image.is_cover, image.position, image.pk)
    )
    videos = [video for video in product.videos.all() if video.embed_url]
    return render(
        request,
        "catalog/product.html",
        {
            "product": product,
            "images": images,
            "videos": videos,
            "slides_total": len(images) + len(videos),
            "is_preview": is_preview,
        },
    )
