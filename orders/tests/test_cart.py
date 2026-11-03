"""Cart, guest checkout, price snapshot, consents, rate limit."""

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from catalog.factories import ProductFactory
from catalog.models import Product
from orders.models import Order
from orders.services import InvalidTransitionError, transition

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    cache.clear()
    yield
    cache.clear()


def add(client, product, **extra):
    return client.post(reverse("orders:add", args=[product.pk]), **extra)


def checkout(client, product, seen_price, **overrides):
    data = {
        "email": "buyer@example.com",
        "email_confirm": "buyer@example.com",
        "consent": "on",
        "seen": f"{product.pk}:{seen_price}",
    }
    data.update(overrides)
    return client.post(reverse("orders:checkout"), data)


class TestCart:
    def test_add_keeps_only_the_id_and_is_idempotent(self, client):
        product = ProductFactory(base_price=45000)
        add(client, product)
        add(client, product)
        assert client.session["cart"] == [product.pk]
        page = client.get(reverse("orders:cart"))
        assert page.status_code == 200
        body = page.content.decode()
        assert product.title in body
        assert "450" in body
        assert 'name="marketing"' not in body
        assert "писем о новых" not in body

    def test_draft_cannot_be_added(self, client):
        product = ProductFactory(status=Product.Status.DRAFT, pdf_file=None)
        response = add(client, product)
        assert response.status_code == 404
        assert client.session.get("cart") in (None, [])

    def test_htmx_add_updates_the_counter(self, client):
        product = ProductFactory()
        response = add(client, product, **HTMX)
        body = response.content.decode()
        assert "В корзине" in body
        assert 'id="cart-count-header"' in body
        assert ">1<" in body

    def test_remove_empties_the_cart(self, client):
        product = ProductFactory()
        add(client, product)
        response = client.post(reverse("orders:remove", args=[product.pk]), **HTMX)
        assert "В корзине пока пусто" in response.content.decode()
        assert client.session["cart"] == []

    def test_header_links_to_the_cart(self, client):
        response = client.get(reverse("home"))
        assert reverse("orders:cart") in response.content.decode()


class TestCheckout:
    def test_creates_order_with_snapshot_and_consent_time(self, client):
        product = ProductFactory(title="Мастер-класс «Лисичка»", base_price=45000)
        add(client, product)
        response = checkout(client, product, 45000, marketing="on")
        assert response.status_code == 302
        order = Order.objects.get()
        assert order.status == Order.Status.CREATED
        assert order.email == "buyer@example.com"
        assert order.total == 45000
        assert order.subtotal == 45000
        assert order.discount_total == 0
        assert order.marketing_consent is False
        assert order.consent_offer_at is not None
        assert order.consent_pdn_at == order.consent_offer_at
        assert order.offer_version
        item = order.items.get()
        assert item.title == "Мастер-класс «Лисичка»"
        assert item.unit_price == 45000
        assert item.price_source == "base"
        assert order.number.startswith(f"K-{timezone.now().year}-")
        assert client.session["cart"] == []
        done = client.get(reverse("orders:done"))
        assert order.number in done.content.decode()

    def test_marketing_defaults_to_false(self, client):
        product = ProductFactory(base_price=40000)
        add(client, product)
        checkout(client, product, 40000)
        assert Order.objects.get().marketing_consent is False

    def test_email_must_match_and_consent_is_required(self, client):
        product = ProductFactory()
        add(client, product)
        mismatch = checkout(client, product, product.base_price, email_confirm="other@example.com")
        assert mismatch.status_code == 200
        assert "не совпадают" in mismatch.content.decode()
        assert Order.objects.count() == 0
        missing = checkout(client, product, product.base_price, consent="")
        assert missing.status_code == 200
        assert Order.objects.count() == 0

    def test_price_change_needs_a_second_confirm(self, client):
        product = ProductFactory(base_price=45000)
        add(client, product)
        product.base_price = 50000
        product.save(update_fields=["base_price"])
        first = checkout(client, product, 45000)
        assert first.status_code == 200
        assert "обновилась" in first.content.decode()
        assert Order.objects.count() == 0
        second = checkout(client, product, 50000)
        assert second.status_code == 302
        assert Order.objects.get().total == 50000

    def test_empty_cart_does_not_create_an_order(self, client):
        response = client.post(
            reverse("orders:checkout"),
            {"email": "a@b.co", "email_confirm": "a@b.co", "consent": "on", "seen": ""},
        )
        assert response.status_code == 302
        assert Order.objects.count() == 0

    def test_checkout_is_rate_limited(self, client):
        product = ProductFactory()
        add(client, product)
        last = None
        for _ in range(9):
            last = checkout(client, product, product.base_price, email="bad")
        assert last.status_code == 429


class TestTransitions:
    def test_illegal_event_is_rejected(self, client):
        product = ProductFactory()
        add(client, product)
        checkout(client, product, product.base_price)
        order = Order.objects.get()
        with pytest.raises(InvalidTransitionError):
            transition(order, "succeeded")
        order.refresh_from_db()
        assert order.status == Order.Status.CREATED

    def test_numbers_increase(self, client):
        first = ProductFactory()
        second = ProductFactory()
        add(client, first)
        checkout(
            client, first, first.base_price, email="a@example.com", email_confirm="a@example.com"
        )
        add(client, second)
        checkout(
            client, second, second.base_price, email="b@example.com", email_confirm="b@example.com"
        )
        numbers = list(Order.objects.order_by("number").values_list("number", flat=True))
        assert numbers[0] < numbers[1]
