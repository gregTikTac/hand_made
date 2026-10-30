"""Management commands: seed_demo and import_media."""

from io import StringIO

import pytest
from django.core.files.storage import storages
from django.core.management import call_command
from django.core.management.base import CommandError

from catalog.factories import MINIMAL_PDF, ProductFactory, make_image_bytes
from catalog.models import Product

pytestmark = pytest.mark.django_db


def run(name, *args, **kwargs) -> str:
    out = StringIO()
    call_command(name, *args, stdout=out, **kwargs)
    return out.getvalue()


class TestSeedDemo:
    def test_creates_requested_count_with_media(self, settings):
        settings.DEBUG = True
        output = run("seed_demo", count=12)
        assert "Всего товаров: 12" in output
        assert Product.objects.count() == 12
        assert Product.objects.published().count() == 12
        assert Product.objects.filter(is_combo=True).exists()
        for product in Product.objects.with_images():
            assert product.cover is not None
            assert product.pdf_file
            assert storages["private"].exists(product.pdf_file.name)

    def test_is_idempotent(self, settings):
        settings.DEBUG = True
        run("seed_demo", count=6)
        output = run("seed_demo", count=6)
        assert "Создано: 0" in output
        assert Product.objects.count() == 6

    def test_first_products_come_from_sample_csv(self, settings):
        settings.DEBUG = True
        run("seed_demo", count=5)
        assert Product.objects.get(slug="lisichka").base_price == 45000
        assert Product.objects.get(slug="plyushevye-kopytca").is_combo is True

    def test_refuses_to_run_without_debug(self, settings):
        settings.DEBUG = False
        with pytest.raises(CommandError):
            run("seed_demo", count=3)
        assert Product.objects.count() == 0


@pytest.fixture
def media_tree(tmp_path):
    folder = tmp_path / "src" / "lisichka"
    (folder / "photos").mkdir(parents=True)
    for number in (10, 2, 1):
        (folder / "photos" / f"photo_{number}.jpg").write_bytes(make_image_bytes())
    (folder / "materials.png").write_bytes(make_image_bytes(fmt="PNG"))
    (folder / "schema.pdf").write_bytes(MINIMAL_PDF)
    (tmp_path / "src" / "unknown-slug").mkdir()
    return tmp_path / "src"


class TestImportMedia:
    def test_attaches_photos_materials_and_pdf(self, media_tree):
        product = ProductFactory(slug="lisichka", pdf_file=None, status=Product.Status.DRAFT)
        output = run("import_media", source=str(media_tree))
        product.refresh_from_db()
        images = list(product.images.order_by("position"))
        assert [image.alt for image in images] == ["photo_1.jpg", "photo_2.jpg", "photo_10.jpg"]
        assert [image.is_cover for image in images] == [True, False, False]
        assert product.materials_image
        assert product.pdf_file and storages["private"].exists(product.pdf_file.name)
        assert "не найдено товаров 1" in output

    def test_is_idempotent(self, media_tree):
        product = ProductFactory(slug="lisichka", pdf_file=None, status=Product.Status.DRAFT)
        run("import_media", source=str(media_tree))
        run("import_media", source=str(media_tree))
        assert product.images.count() == 3

    def test_existing_pdf_kept_unless_overwrite(self, media_tree):
        product = ProductFactory(slug="lisichka")
        original = product.pdf_file.name
        run("import_media", source=str(media_tree))
        product.refresh_from_db()
        assert product.pdf_file.name == original
        run("import_media", source=str(media_tree), overwrite=True)
        product.refresh_from_db()
        assert product.pdf_file.name != original

    def test_dry_run_writes_nothing(self, media_tree):
        product = ProductFactory(slug="lisichka", pdf_file=None, status=Product.Status.DRAFT)
        output = run("import_media", source=str(media_tree), dry_run=True)
        assert "dry-run" in output
        assert product.images.count() == 0

    def test_missing_source_is_an_error(self, tmp_path):
        with pytest.raises(CommandError):
            run("import_media", source=str(tmp_path / "nope"))
