"""Custom model/form fields."""

from decimal import Decimal

from django import forms
from django.db import models

from core.money import kopecks_to_rubles, rubles_to_kopecks


class RubleFormField(forms.DecimalField):
    """Form field: the user types rubles, the cleaned value is integer kopecks."""

    def __init__(self, **kwargs):
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("max_digits", 10)
        kwargs.setdefault("min_value", Decimal("0"))
        super().__init__(**kwargs)

    def prepare_value(self, value):
        """Show kopecks as rubles: 45000 -> "450", 45050 -> "450.50"."""
        if isinstance(value, int) and not isinstance(value, bool):
            rubles, rest = divmod(value, 100)
            return f"{rubles}.{rest:02d}" if rest else str(rubles)
        return value

    def clean(self, value):
        rubles = super().clean(value)
        return None if rubles is None else rubles_to_kopecks(rubles)

    def has_changed(self, initial, data):
        if isinstance(initial, int) and not isinstance(initial, bool):
            initial = kopecks_to_rubles(initial)
        return super().has_changed(initial, data)


class KopecksField(models.PositiveIntegerField):
    """Money stored as integer kopecks; forms (admin) work in rubles."""

    description = "Сумма в копейках"

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", RubleFormField)
        # Drop integer-specific kwargs that DecimalField does not accept.
        kwargs.pop("min_value", None)
        kwargs.pop("max_value", None)
        return super().formfield(**kwargs)
