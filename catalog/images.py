"""Responsive image variants: webp in several widths generated with Pillow (ADR-0006)."""

import logging
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Widths from ARCHITECTURE §10 (360/720/1080); the original stays as the jpeg/png fallback.
VARIANT_WIDTHS = (360, 720, 1080)
WEBP_QUALITY = 82


def variant_widths(original_width: int) -> list[int]:
    """Widths of generated variants: never upscale, the largest is capped by the original."""
    return sorted({min(width, original_width) for width in VARIANT_WIDTHS})


def variant_name(name: str, width: int) -> str:
    """``products/a.jpg`` -> ``products/a.jpg.720.webp`` (extension kept: a.jpg and a.png never clash)."""
    return f"{name}.{width}.webp"


def generate_variants(field_file) -> list[int]:
    """Create webp variants for an ImageFieldFile. Returns the generated widths."""
    storage = field_file.storage
    field_file.open("rb")
    try:
        with Image.open(field_file) as source:
            image = ImageOps.exif_transpose(source)
            image.load()
    finally:
        field_file.close()

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")

    widths = variant_widths(image.width)
    for width in widths:
        resized = image if width == image.width else _resize(image, width)
        buffer = BytesIO()
        resized.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=4)
        name = variant_name(field_file.name, width)
        if storage.exists(name):
            storage.delete(name)
        storage.save(name, ContentFile(buffer.getvalue()))
    return widths


def _resize(image: Image.Image, width: int) -> Image.Image:
    height = max(1, round(image.height * width / image.width))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def delete_variants(field_file, original_width: int | None = None) -> None:
    """Remove generated variants (and nothing else) of an image."""
    if not field_file or not field_file.name:
        return
    storage = field_file.storage
    widths = variant_widths(original_width) if original_width else VARIANT_WIDTHS
    for width in widths:
        name = variant_name(field_file.name, width)
        try:
            if storage.exists(name):
                storage.delete(name)
        except Exception:  # noqa: BLE001 — cleanup must never break deletion
            logger.warning("Could not delete image variant %s", name, exc_info=True)


def srcset(field_file, original_width: int | None) -> str:
    """``srcset`` string for the generated webp variants."""
    if not field_file or not original_width:
        return ""
    return ", ".join(
        f"{field_file.storage.url(variant_name(field_file.name, width))} {width}w"
        for width in variant_widths(original_width)
    )
