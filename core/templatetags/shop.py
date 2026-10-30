"""Template helpers for the storefront."""

from django import template
from django.utils.html import format_html

from core.money import format_rub

register = template.Library()


@register.filter
def rub(kopecks):
    """``45000|rub`` -> ``450 ₽`` (non-breaking spaces)."""
    return format_rub(kopecks)


@register.simple_tag
def picture(image, sizes, alt="", css_class="", eager=False):
    """Responsive ``<picture>``: webp ``srcset`` + original as the fallback.

    ``image`` is a ``ProductImage``; ``width``/``height`` are always set (no layout shift).
    """
    if not image or not image.image:
        return ""
    attrs = {
        "src": image.image.url,
        "alt": alt or image.alt,
        "class": css_class,
        "loading": "eager" if eager else "lazy",
        "decoding": "async",
        "width": image.image_width or "",
        "height": image.image_height or "",
    }
    if eager:
        attrs["fetchpriority"] = "high"
    img = format_html(
        "<img {}>",
        format_html(" ".join(f'{key}="{{}}"' for key in attrs), *attrs.values()),
    )
    srcset = image.srcset
    if not srcset:
        return img
    return format_html(
        '<picture><source type="image/webp" srcset="{}" sizes="{}">{}</picture>', srcset, sizes, img
    )


@register.simple_tag
def materials_picture(product, sizes):
    """``<picture>`` for the "required materials" photo of a product."""
    from catalog import images as image_utils

    if not product.materials_image:
        return ""
    srcset = image_utils.srcset(product.materials_image, product.materials_image_width)
    img = format_html(
        '<img src="{}" alt="Необходимые материалы: {}" loading="lazy" decoding="async" '
        'width="{}" height="{}">',
        product.materials_image.url,
        product.title,
        product.materials_image_width or "",
        product.materials_image_height or "",
    )
    if not srcset:
        return img
    return format_html(
        '<picture><source type="image/webp" srcset="{}" sizes="{}">{}</picture>', srcset, sizes, img
    )
