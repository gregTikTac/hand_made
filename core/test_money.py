"""Money helpers and the ruble form field."""

import pytest
from django.core.exceptions import ValidationError

from core.fields import RubleFormField
from core.money import format_rub, kopecks_to_rubles, rubles_to_kopecks


def test_conversions():
    assert rubles_to_kopecks("450") == 45000
    assert rubles_to_kopecks("450.50") == 45050
    assert rubles_to_kopecks("0.005") == 1  # half up
    assert str(kopecks_to_rubles(45050)) == "450.50"


def test_format_rub():
    assert format_rub(45000) == "450\u00a0₽"
    assert format_rub(129000) == "1\u00a0290\u00a0₽"
    assert format_rub(45050) == "450,50\u00a0₽"
    assert format_rub(None) == ""


def test_ruble_form_field_roundtrip():
    field = RubleFormField()
    assert field.clean("450") == 45000
    assert field.clean("450.50") == 45050
    assert field.prepare_value(45000) == "450"
    assert field.prepare_value(45050) == "450.50"
    assert field.has_changed(45000, "450") is False
    assert field.has_changed(45000, "451") is True


def test_ruble_form_field_rejects_negative():
    with pytest.raises(ValidationError):
        RubleFormField().clean("-1")
