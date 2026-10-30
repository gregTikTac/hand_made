"""Product page: details, gallery, video, materials, preview for staff, escaping."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from catalog.factories import (
    ProductFactory,
    ProductImageFactory,
    ProductVideoFactory,
    make_image_bytes,
)
from catalog.models import Product

pytestmark = pytest.mark.django_db


def test_renders_details(client):
    product = ProductFactory(
        title="Козлёнок Боря",
        description="Первый абзац",
        height_cm=25,
        construction="цельно вязаный",
        videos_count=1,
        clothing_included=True,
    )
    ProductImageFactory(product=product)
    response = client.get(product.get_absolute_url())
    html = response.content.decode()
    assert response.status_code == 200
    for text in ("Козлёнок Боря", "Первый абзац", "высота 25 см", "Цельно вязаный", "одежды"):
        assert text in html
    assert 'rel="canonical"' in html and 'property="og:title"' in html


def test_gallery_has_all_photos_and_lazy_video(client):
    product = ProductFactory()
    for _ in range(3):
        ProductImageFactory(product=product)
    ProductVideoFactory(product=product)
    html = client.get(product.get_absolute_url()).content.decode()
    assert html.count('class="gallery__slide"') == 4  # 3 photos + 1 video
    assert html.count('class="gallery__thumb"') == 4
    # the iframe lives inside an Alpine template that renders only after a click
    assert "youtube-nocookie.com/embed/" in html
    assert '<template x-if="play">' in html
    assert "<iframe" in html and html.index("<iframe") > html.index('<template x-if="play">')


def test_first_photo_is_eager_others_lazy(client):
    product = ProductFactory()
    for _ in range(2):
        ProductImageFactory(product=product)
    html = client.get(product.get_absolute_url()).content.decode()
    assert html.count('loading="eager"') == 1
    assert 'fetchpriority="high"' in html


def test_page_without_photos_still_renders(client):
    html = client.get(ProductFactory().get_absolute_url()).content.decode()
    assert "Фото скоро появится" in html


def test_materials_photo_shown_only_when_uploaded(client):
    product = ProductFactory()
    assert "Необходимые материалы" not in client.get(product.get_absolute_url()).content.decode()
    product.materials_image.save("m.jpg", ContentFile(make_image_bytes()), save=True)
    html = client.get(product.get_absolute_url()).content.decode()
    assert "Необходимые материалы" in html and 'class="materials__photo"' in html


def test_unknown_slug_is_404(client):
    assert client.get("/p/net-takogo/").status_code == 404


def test_draft_hidden_from_public(client):
    draft = ProductFactory(status=Product.Status.DRAFT, pdf_file=None)
    assert client.get(draft.get_absolute_url()).status_code == 404


def test_draft_preview_for_staff_is_noindex(client):
    draft = ProductFactory(status=Product.Status.DRAFT, pdf_file=None)
    staff = get_user_model().objects.create_user("st", "s@e.com", "x", is_staff=True)
    client.force_login(staff)
    response = client.get(draft.get_absolute_url())
    html = response.content.decode()
    assert response.status_code == 200
    assert 'content="noindex"' in html and "Предпросмотр" in html


def test_contact_links_shown_when_configured(client, settings):
    settings.VK_URL = "https://vk.com/baloo_hand"
    html = client.get(ProductFactory().get_absolute_url()).content.decode()
    assert "https://vk.com/baloo_hand" in html and "Остались вопросы?" in html
    assert 'rel="noopener noreferrer"' in html


def test_no_questions_block_without_links(client):
    html = client.get(ProductFactory().get_absolute_url()).content.decode()
    assert "Остались вопросы?" not in html


def test_description_is_escaped(client):
    product = ProductFactory(description="<img src=x onerror=alert(1)>")
    html = client.get(product.get_absolute_url()).content.decode()
    assert "<img src=x onerror" not in html


def test_price_comes_from_pricing_not_raw_field(client):
    product = ProductFactory(base_price=59000, compare_price=70000)
    html = client.get(product.get_absolute_url()).content.decode()
    assert "590\u00a0₽" in html and "700\u00a0₽" in html
