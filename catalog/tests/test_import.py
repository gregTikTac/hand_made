"""CSV import/export of products using the real sample file from docs/brief."""

from pathlib import Path

import pytest
import tablib

from catalog.factories import ProductFactory
from catalog.models import Product
from catalog.resources import ProductResource, parse_bool

pytestmark = pytest.mark.django_db

SAMPLE_CSV = Path(__file__).resolve().parents[2] / "docs" / "brief" / "sample-products.csv"


def load_sample() -> tablib.Dataset:
    return tablib.Dataset().load(SAMPLE_CSV.read_text(encoding="utf-8"), format="csv")


def test_sample_csv_imports_four_products():
    result = ProductResource().import_data(load_sample(), raise_errors=True)
    assert not result.has_errors()
    assert Product.objects.count() == 4
    fox = Product.objects.get(slug="lisichka")
    assert fox.title == "Мастер-класс «Лисичка»"
    assert fox.base_price == 45000  # kopecks, as in the sample file
    assert fox.height_cm == 30 and fox.length_cm is None
    assert fox.clothing_included is True
    assert fox.videos_count == 0
    assert "цельно вязаная" in fox.construction


def test_combo_category_and_flags():
    ProductResource().import_data(load_sample(), raise_errors=True)
    combo = Product.objects.get(slug="plyushevye-kopytca")
    assert combo.is_combo is True
    assert combo.videos_count == 7
    assert combo.base_price == 60000
    assert Product.objects.get(slug="zabavnye-ovechki").is_combo is False
    assert Product.objects.get(slug="zabavnye-ovechki").clothing_included is False


def test_imported_products_are_drafts():
    ProductResource().import_data(load_sample(), raise_errors=True)
    assert set(Product.objects.values_list("status", flat=True)) == {Product.Status.DRAFT}


def test_reimport_updates_instead_of_duplicating_and_keeps_status():
    ProductResource().import_data(load_sample(), raise_errors=True)
    Product.objects.filter(slug="lisichka").update(status=Product.Status.PUBLISHED)
    dataset = load_sample()
    result = ProductResource().import_data(dataset, raise_errors=True)
    assert not result.has_errors()
    assert Product.objects.count() == 4
    assert Product.objects.get(slug="lisichka").status == Product.Status.PUBLISHED


def test_reimport_changes_price():
    ProductFactory(slug="lisichka", title="Старое", base_price=10000)
    ProductResource().import_data(load_sample(), raise_errors=True)
    assert Product.objects.get(slug="lisichka").base_price == 45000


def test_row_without_slug_is_an_error():
    dataset = tablib.Dataset(headers=["slug", "title", "base_price"])
    dataset.append(["", "Без адреса", "45000"])
    result = ProductResource().import_data(dataset, raise_errors=False)
    assert result.has_errors() or result.has_validation_errors()
    assert Product.objects.count() == 0


def test_zero_price_row_is_rejected():
    dataset = tablib.Dataset(headers=["slug", "title", "base_price"])
    dataset.append(["free", "Бесплатно", "0"])
    result = ProductResource().import_data(dataset, raise_errors=False)
    assert result.has_errors() or result.has_validation_errors()
    assert not Product.objects.filter(slug="free").exists()


def test_export_roundtrip():
    ProductResource().import_data(load_sample(), raise_errors=True)
    exported = ProductResource().export()
    assert len(exported) == 4
    rows = {row["slug"]: row for row in exported.dict}
    assert rows["plyushevye-kopytca"]["category"] == "combo"
    assert rows["lisichka"]["category"] == "single"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("yes", True),
        ("да", True),
        ("1", True),
        ("no", False),
        ("нет", False),
        ("", False),
        (None, False),
    ],
)
def test_parse_bool(value, expected):
    assert parse_bool(value) is expected


def test_parse_bool_rejects_garbage():
    with pytest.raises(ValueError):
        parse_bool("maybe")
