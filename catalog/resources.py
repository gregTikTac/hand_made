"""CSV import/export of products (django-import-export).

CSV format = ``docs/brief/sample-products.csv``:
``slug,title,base_price,format,height_cm,length_cm,category,videos_count,construction,
clothing_included,support,cover_photo,photo_count,description``.

* ``base_price`` / ``compare_price`` are integer KOPECKS (45000 = 450 ₽), like in the sample file.
* ``category``: ``combo`` marks a combo, anything else (``single``) is a regular product.
* ``clothing_included``: yes/no/да/нет/1/0/true/false.
* Unknown columns (format, support, cover_photo, photo_count) are ignored.
* Products are matched by ``slug`` (update if exists, create otherwise); new ones become drafts,
  because the PDF is attached later (``import_media``).
"""

from import_export import fields, resources

from catalog.models import Product

_TRUE = {"1", "true", "yes", "y", "да", "д"}
_FALSE = {"", "0", "false", "no", "n", "нет", "н"}


def parse_bool(value) -> bool:
    text = str(value if value is not None else "").strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise ValueError(f"Не удалось понять значение «{value}»: используйте да/нет")


def _int_or_none(value):
    text = str(value if value is not None else "").strip()
    return int(text) if text else None


class ProductResource(resources.ModelResource):
    category = fields.Field(column_name="category", attribute="is_combo", readonly=False)

    class Meta:
        model = Product
        import_id_fields = ("slug",)
        fields = (
            "slug",
            "title",
            "base_price",
            "compare_price",
            "height_cm",
            "length_cm",
            "videos_count",
            "construction",
            "clothing_included",
            "description",
            "short_description",
            "status",
            "category",
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = True
        clean_model_instances = True
        use_transactions = True

    def before_import_row(self, row, **kwargs):
        """Normalise sample-file conventions into model values."""
        slug = str(row.get("slug") or "").strip()
        if not slug:
            raise ValueError("Пустой slug: у каждой строки должен быть адрес товара")
        row["slug"] = slug
        row["category"] = str(row.get("category", "")).strip().lower() == "combo"
        row["clothing_included"] = parse_bool(row.get("clothing_included"))
        for key in ("height_cm", "length_cm", "compare_price"):
            row[key] = _int_or_none(row.get(key))
        row["base_price"] = _int_or_none(row.get("base_price"))
        row["videos_count"] = _int_or_none(row.get("videos_count")) or 0
        if not str(row.get("status") or "").strip():
            # Do not touch the status of existing products; new ones start as drafts.
            row.pop("status", None)
        super().before_import_row(row, **kwargs)

    def dehydrate_category(self, product):
        return "combo" if product.is_combo else "single"
