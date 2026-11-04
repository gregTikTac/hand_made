"""Stamp the buyer's email on every PDF page. pypdf merges, reportlab draws the line."""

import os
from io import BytesIO

from django.core.exceptions import ImproperlyConfigured

FONT_CANDIDATES = (
    os.environ.get("WATERMARK_FONT", ""),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
)


class WatermarkError(Exception):
    """The PDF could not be stamped. The original file is left untouched."""


def cyrillic_font() -> str:
    for path in FONT_CANDIDATES:
        if path and os.path.isfile(path):
            return path
    raise ImproperlyConfigured(
        "Нет шрифта с кириллицей для пометки PDF. Установите fonts-dejavu-core "
        "или укажите WATERMARK_FONT."
    )


def stamp_pdf(data: bytes, text: str) -> bytes:
    """Return a new PDF with ``text`` at the bottom of each page."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.colors import Color
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise WatermarkError("Файл не читается как PDF") from exc
    if reader.is_encrypted:
        raise WatermarkError("PDF закрыт паролем, пометку поставить нельзя")
    if not reader.pages:
        raise WatermarkError("В PDF нет страниц")

    if "StampFont" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("StampFont", cyrillic_font()))

    writer = PdfWriter()
    line = text.replace("\n", " ")[:180]
    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        drawing = canvas.Canvas(packet, pagesize=(width, height))
        drawing.setFillColor(Color(0.45, 0.08, 0.14, alpha=0.55))
        drawing.setFont("StampFont", 8)
        drawing.drawString(28, 22, line)
        drawing.save()
        packet.seek(0)
        page.merge_page(PdfReader(packet).pages[0])
        writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()
