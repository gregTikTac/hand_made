"""Checkout form. Newsletter consent is not collected."""

from django import forms


class CheckoutForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "autocomplete": "email",
                "inputmode": "email",
                "placeholder": "you@example.ru",
            }
        ),
        error_messages={"invalid": "Проверьте адрес: похоже, в нём ошибка."},
    )
    email_confirm = forms.EmailField(
        label="Повторите email",
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "autocomplete": "off",
                "inputmode": "email",
                "placeholder": "you@example.ru",
            }
        ),
    )
    consent = forms.BooleanField(
        label="Оферта и персональные данные",
        error_messages={"required": "Нужно согласие с офертой и на обработку персональных данных."},
    )
    seen = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        confirm = (cleaned.get("email_confirm") or "").strip().lower()
        if email and confirm and email != confirm:
            self.add_error("email_confirm", "Адреса не совпадают. Введите один и тот же email.")
        return cleaned
