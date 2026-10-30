"""Storefront catalog: list, tabs, HTMX 'show more', card markup, home page."""

import re
from pathlib import Path

import pytest
from django.urls import reverse

from catalog.factories import ProductFactory, ProductImageFactory
from catalog.models import Product
from catalog.views import PAGE_SIZE

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}
CSS = Path(__file__).resolve().parents[2] / "static" / "css" / "components.css"


def cards(html: str) -> int:
    return html.count('<article class="card">')


def make_products(count, **kwargs):
    return [ProductFactory(sort_order=i, **kwargs) for i in range(count)]


class TestCatalogList:
    def test_shows_only_published(self, client):
        ProductFactory(title="Видимый")
        ProductFactory(title="Черновик", status=Product.Status.DRAFT, pdf_file=None)
        ProductFactory(title="Архивный", status=Product.Status.ARCHIVED)
        html = client.get(reverse("catalog:list")).content.decode()
        assert "Видимый" in html
        assert "Черновик" not in html and "Архивный" not in html

    def test_grid_is_two_columns_always(self, client):
        make_products(3)
        html = client.get(reverse("catalog:list")).content.decode()
        assert '<ul class="product-grid" id="product-grid">' in html
        # base rule (no media query) = 2 columns, so 390px is covered
        assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in CSS.read_text(encoding="utf-8")

    def test_page_size_is_even_so_rows_stay_full(self):
        assert PAGE_SIZE % 2 == 0

    def test_first_page_has_page_size_cards_and_show_more(self, client):
        make_products(PAGE_SIZE + 3)
        html = client.get(reverse("catalog:list")).content.decode()
        assert cards(html) == PAGE_SIZE
        assert "Показать ещё" in html and "?page=2" in html

    def test_no_show_more_when_everything_fits(self, client):
        make_products(3)
        assert "Показать ещё" not in client.get(reverse("catalog:list")).content.decode()

    def test_htmx_returns_fragment_with_next_cards_and_oob_control(self, client):
        make_products(PAGE_SIZE + 3)
        response = client.get(reverse("catalog:list") + "?page=2", **HTMX)
        html = response.content.decode()
        assert "<html" not in html
        assert cards(html) == 3
        assert 'hx-swap-oob="true"' in html
        assert "Показать ещё" not in html  # last page: control emptied
        assert "HX-Request" in response["Vary"]

    def test_htmx_middle_page_points_to_next(self, client):
        make_products(PAGE_SIZE * 2 + 1)
        html = client.get(reverse("catalog:list") + "?page=2", **HTMX).content.decode()
        assert cards(html) == PAGE_SIZE
        assert "?page=3" in html

    @pytest.mark.parametrize("page", ["99", "0", "abc", "-1"])
    def test_bad_page_is_404(self, client, page):
        make_products(2)
        assert client.get(reverse("catalog:list") + f"?page={page}").status_code == 404

    def test_empty_catalog_shows_message(self, client):
        response = client.get(reverse("catalog:list"))
        assert response.status_code == 200
        assert "Здесь пока пусто" in response.content.decode()

    def test_combo_tab_and_counts(self, client):
        ProductFactory(title="Одиночка")
        ProductFactory(title="Набор", is_combo=True)
        html = client.get(reverse("catalog:combo")).content.decode()
        assert "Набор" in html and "Одиночка" not in html
        all_html = client.get(reverse("catalog:list")).content.decode()
        assert re.search(r'Все <span class="tab__count">2</span>', all_html)
        assert re.search(r'Комбо <span class="tab__count">1</span>', all_html)
        assert "badge badge--combo" in all_html

    def test_only_get_allowed(self, client):
        assert client.post(reverse("catalog:list")).status_code == 405

    def test_query_count_does_not_grow_with_products(self, client, django_assert_max_num_queries):
        for product in make_products(PAGE_SIZE):
            ProductImageFactory(product=product)
        with django_assert_max_num_queries(8):
            assert client.get(reverse("catalog:list")).status_code == 200


class TestCardMarkup:
    def test_price_srcset_lazy_and_dimensions(self, client):
        product = ProductFactory(base_price=45000, compare_price=60000)
        ProductImageFactory(product=product)
        html = client.get(reverse("catalog:list")).content.decode()
        assert "450\u00a0₽" in html and "600\u00a0₽" in html
        assert 'type="image/webp"' in html and "srcset=" in html
        assert 'loading="lazy"' in html and 'width="800"' in html

    def test_card_without_photo_shows_placeholder(self, client):
        ProductFactory()
        assert "card__media--empty" in client.get(reverse("catalog:list")).content.decode()

    def test_title_is_escaped(self, client):
        ProductFactory(title="<script>alert(1)</script>")
        html = client.get(reverse("catalog:list")).content.decode()
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html


class TestHome:
    def test_popular_products_by_popularity(self, client):
        ProductFactory(title="Скромный", popularity=1)
        ProductFactory(title="Хит", popularity=999)
        html = client.get(reverse("home")).content.decode()
        assert html.index("Хит") < html.index("Скромный")

    def test_home_limits_to_four_cards(self, client):
        make_products(7)
        assert cards(client.get(reverse("home")).content.decode()) == 4

    def test_home_links_to_catalog(self, client):
        assert reverse("catalog:list") in client.get(reverse("home")).content.decode()
