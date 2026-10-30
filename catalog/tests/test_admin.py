"""Admin: pages render, product form works in rubles, publishing rules, inlines."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from catalog.factories import MINIMAL_PDF, ProductFactory, ProductImageFactory, make_image_bytes
from catalog.models import Product, ProductVideo

pytestmark = pytest.mark.django_db

EMPTY_INLINES = {
    "images-TOTAL_FORMS": "0",
    "images-INITIAL_FORMS": "0",
    "videos-TOTAL_FORMS": "0",
    "videos-INITIAL_FORMS": "0",
}


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pass12345")
    client.force_login(user)
    return client


def product_form(product, **overrides):
    data = {
        "title": product.title,
        "status": "published",
        "base_price": "450",
        "slug": product.slug,
        "sort_order": "0",
        "popularity": "0",
        "videos_count": "0",
        **EMPTY_INLINES,
    }
    data.update(overrides)
    return data


def test_changelist_pages_render(admin_client):
    ProductImageFactory(product=ProductFactory(title="Лисичка"))
    for name in ("catalog_product_changelist", "catalog_category_changelist"):
        assert admin_client.get(reverse(f"admin:{name}")).status_code == 200
    page = admin_client.get(reverse("admin:catalog_product_changelist")).content.decode()
    assert "Лисичка" in page


def test_add_change_and_import_pages_render(admin_client):
    product = ProductFactory()
    assert admin_client.get(reverse("admin:catalog_product_add")).status_code == 200
    response = admin_client.get(reverse("admin:catalog_product_change", args=[product.pk]))
    assert response.status_code == 200
    assert 'value="450"' in response.content.decode()  # rubles, not kopecks
    assert admin_client.get(reverse("admin:catalog_product_import")).status_code == 200


def test_create_product_with_rubles_photo_and_video(admin_client):
    product = ProductFactory.build(title="Козлёнок Боря")
    data = product_form(
        product,
        slug="",
        description="Описание",
        height_cm="25",
        pdf_file=SimpleUploadedFile("a.pdf", MINIMAL_PDF, content_type="application/pdf"),
        **{
            "images-TOTAL_FORMS": "1",
            "images-0-image": SimpleUploadedFile("p.jpg", make_image_bytes(), "image/jpeg"),
            "images-0-alt": "Боря",
            "images-0-is_cover": "on",
            "images-0-position": "0",
            "videos-TOTAL_FORMS": "1",
            "videos-0-url": "https://youtu.be/dQw4w9WgXcQ",
            "videos-0-title": "Сложный момент",
            "videos-0-position": "0",
        },
    )
    response = admin_client.post(reverse("admin:catalog_product_add"), data)
    assert response.status_code == 302, response.content.decode()[:1500]
    created = Product.objects.get(slug="kozlyonok-borya")
    assert created.base_price == 45000
    assert created.images.count() == 1 and created.images.get().is_cover
    assert created.videos.get().provider == "youtube"


def test_publish_without_pdf_is_rejected_in_form(admin_client):
    product = ProductFactory(status=Product.Status.DRAFT, pdf_file=None)
    response = admin_client.post(
        reverse("admin:catalog_product_change", args=[product.pk]), product_form(product)
    )
    assert response.status_code == 200  # form re-rendered with an error
    assert "Нельзя опубликовать" in response.content.decode()
    product.refresh_from_db()
    assert product.status == Product.Status.DRAFT


def test_bad_video_url_rejected_in_form(admin_client):
    product = ProductFactory()
    data = product_form(
        product,
        **{
            "videos-TOTAL_FORMS": "1",
            "videos-0-url": "https://example.com/movie.mp4",
            "videos-0-position": "0",
        },
    )
    response = admin_client.post(reverse("admin:catalog_product_change", args=[product.pk]), data)
    assert response.status_code == 200
    assert ProductVideo.objects.count() == 0


def _run_action(admin_client, name, products):
    return admin_client.post(
        reverse("admin:catalog_product_changelist"),
        {"action": name, "_selected_action": [p.pk for p in products]},
        follow=True,
    )


def test_publish_action_skips_products_without_pdf(admin_client):
    ready = ProductFactory(status=Product.Status.DRAFT)
    no_pdf = ProductFactory(status=Product.Status.DRAFT, pdf_file=None)
    response = _run_action(admin_client, "publish", [ready, no_pdf])
    ready.refresh_from_db()
    no_pdf.refresh_from_db()
    assert ready.status == Product.Status.PUBLISHED
    assert no_pdf.status == Product.Status.DRAFT
    assert "нет PDF" in response.content.decode()


def test_unpublish_and_archive_actions(admin_client):
    product = ProductFactory()
    _run_action(admin_client, "unpublish", [product])
    product.refresh_from_db()
    assert product.status == Product.Status.DRAFT
    _run_action(admin_client, "archive", [product])
    product.refresh_from_db()
    assert product.status == Product.Status.ARCHIVED


def test_category_slug_autofilled_in_admin(admin_client):
    from catalog.models import Category

    response = admin_client.post(
        reverse("admin:catalog_category_add"),
        {"title": "Для начинающих", "slug": "", "position": "0", "is_visible": "on"},
    )
    assert response.status_code == 302
    assert Category.objects.get().slug == "dlya-nachinayushchikh"
