"""Model behaviour: slugs, price constraints, publishing rules, PDF storage, cover."""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.db import IntegrityError, transaction

from catalog.factories import (
    MINIMAL_PDF,
    CategoryFactory,
    ProductFactory,
    ProductImageFactory,
)
from catalog.models import Product, ProductImage
from core.text import slugify_ru

pytestmark = pytest.mark.django_db


class TestSlugs:
    def test_transliteration(self):
        assert slugify_ru("Козлёнок Боря") == "kozlyonok-borya"
        assert slugify_ru("Мастер-класс «Лисичка»") == "master-klass-lisichka"

    def test_slug_generated_from_title(self):
        assert ProductFactory(title="Козлёнок Боря").slug == "kozlyonok-borya"

    def test_slug_collision_gets_suffix(self):
        first = ProductFactory(title="Лисичка")
        second = ProductFactory(title="Лисичка")
        assert first.slug == "lisichka"
        assert second.slug == "lisichka-2"

    def test_explicit_slug_is_kept(self):
        assert ProductFactory(title="Лисичка", slug="fox").slug == "fox"

    def test_category_slug(self):
        assert CategoryFactory(title="Для начинающих").slug == "dlya-nachinayushchikh"


class TestPriceConstraints:
    def test_zero_price_rejected_by_db(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            ProductFactory(base_price=0)

    def test_compare_price_must_exceed_base(self):
        product = ProductFactory.build(base_price=45000, compare_price=40000)
        with pytest.raises(ValidationError) as exc:
            product.clean()
        assert "compare_price" in exc.value.message_dict

    def test_compare_price_greater_is_ok(self):
        ProductFactory.build(base_price=45000, compare_price=60000).clean()


class TestPublishing:
    def test_published_without_pdf_rejected(self):
        product = ProductFactory.build(pdf_file=None, status=Product.Status.PUBLISHED)
        with pytest.raises(ValidationError) as exc:
            product.clean()
        assert "pdf_file" in exc.value.message_dict

    def test_draft_without_pdf_allowed(self):
        ProductFactory.build(pdf_file=None, status=Product.Status.DRAFT).clean()

    def test_published_combo_without_pdf_allowed(self):
        ProductFactory.build(pdf_file=None, is_combo=True, status=Product.Status.PUBLISHED).clean()

    def test_published_queryset(self):
        published = ProductFactory()
        ProductFactory(status=Product.Status.DRAFT, pdf_file=None)
        ProductFactory(status=Product.Status.ARCHIVED)
        assert list(Product.objects.published()) == [published]


class TestPdfStorage:
    def test_pdf_goes_to_private_storage_only(self):
        product = ProductFactory()
        assert storages["private"].exists(product.pdf_file.name)
        assert not storages["default"].exists(product.pdf_file.name)
        assert product.pdf_file.name.startswith("pdf/")
        assert product.pdf_file.read() == MINIMAL_PDF

    def test_random_file_name_does_not_leak_original(self):
        product = ProductFactory(pdf_file=ContentFile(MINIMAL_PDF, name="Секретное имя.pdf"))
        assert "Секретное" not in product.pdf_file.name

    def test_fake_pdf_rejected(self):
        product = ProductFactory.build(pdf_file=ContentFile(b"<html>not pdf</html>", name="x.pdf"))
        with pytest.raises(ValidationError) as exc:
            product.full_clean(exclude=["slug"])
        assert "pdf_file" in exc.value.message_dict

    def test_non_pdf_extension_rejected(self):
        product = ProductFactory.build(pdf_file=ContentFile(MINIMAL_PDF, name="x.exe"))
        with pytest.raises(ValidationError) as exc:
            product.full_clean(exclude=["slug"])
        assert "pdf_file" in exc.value.message_dict


class TestCover:
    def test_no_images_no_cover(self):
        assert ProductFactory().cover is None

    def test_first_by_position_is_cover_by_default(self):
        product = ProductFactory()
        ProductImageFactory(product=product, position=2)
        first = ProductImageFactory(product=product, position=1)
        assert Product.objects.get(pk=product.pk).cover == first

    def test_flagged_cover_wins(self):
        product = ProductFactory()
        ProductImageFactory(product=product, position=1)
        flagged = ProductImageFactory(product=product, position=5, is_cover=True)
        assert Product.objects.get(pk=product.pk).cover == flagged

    def test_setting_new_cover_demotes_previous(self):
        product = ProductFactory()
        old = ProductImageFactory(product=product, is_cover=True)
        new = ProductImageFactory(product=product, is_cover=True)
        old.refresh_from_db()
        assert (old.is_cover, new.is_cover) == (False, True)
        assert product.images.filter(is_cover=True).count() == 1

    def test_db_allows_only_one_cover(self):
        product = ProductFactory()
        ProductImageFactory(product=product, is_cover=True)
        other = ProductImageFactory(product=product)
        with pytest.raises(IntegrityError), transaction.atomic():
            ProductImage.objects.filter(pk=other.pk).update(is_cover=True)

    def test_with_images_prefetch_avoids_n_plus_one(self, django_assert_num_queries):
        for _ in range(3):
            ProductImageFactory(product=ProductFactory())
        with django_assert_num_queries(2):
            products = list(Product.objects.published().with_images())
            assert all(product.cover is not None for product in products)
