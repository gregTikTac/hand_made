"""Which PDFs a purchase should deliver.

A combo hands out each toy's own PDF (the client's answer). If the combo has no
parts yet, its own PDF is used so the buyer still receives a file.
"""

from catalog.models import ComboItem


def source_pdfs(product) -> list[tuple[str, object]]:
    if product.is_combo:
        parts = []
        rows = (
            ComboItem.objects.filter(combo=product)
            .select_related("item")
            .order_by("position", "id")
        )
        for row in rows:
            if row.item.pdf_file:
                parts.append((row.item.title, row.item.pdf_file))
        if parts:
            return parts
    if product.pdf_file:
        return [(product.title, product.pdf_file)]
    return []
