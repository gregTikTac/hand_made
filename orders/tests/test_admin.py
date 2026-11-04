"""The order list no longer offers the newsletter column."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_changelist_hides_newsletter(client):
    user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pass12345")
    client.force_login(user)
    response = client.get(reverse("admin:orders_order_changelist"))
    body = response.content.decode()
    assert response.status_code == 200
    assert "Согласие на рассылку" not in body
    assert "marketing" not in body
