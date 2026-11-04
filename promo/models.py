"""Shop-wide sales and preorders. Discounts do not stack: pricing.py keeps the larger one."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class DiscountCampaign(models.Model):
    title = models.CharField(
        "Название", max_length=120, help_text="Эту фразу увидят на полоске сверху."
    )
    percent = models.PositiveSmallIntegerField(
        "Скидка, %",
        help_text="От 1 до 90. Скидка предзаказа с ней не складывается: берётся большая.",
    )
    starts_at = models.DateTimeField("Начало")
    ends_at = models.DateTimeField("Конец")
    is_active = models.BooleanField(
        "Включена", default=True, help_text="Снимите галочку, чтобы остановить акцию раньше срока."
    )
    exclude_preorders = models.BooleanField(
        "Не применять к предзаказам",
        default=False,
        help_text="Если включено, у предзаказа остаётся только его собственная скидка.",
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "акция"
        verbose_name_plural = "акции"
        ordering = ("-starts_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(percent__gte=1, percent__lte=90), name="campaign_percent_1_90"
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="campaign_ends_after_start"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} −{self.percent}%"

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Окончание должно быть позже начала."})
        if self.percent is not None and not 1 <= self.percent <= 90:
            raise ValidationError({"percent": "Процент от 1 до 90."})
        if not self.is_active or not self.starts_at or not self.ends_at:
            return
        overlap = DiscountCampaign.objects.filter(
            is_active=True, starts_at__lt=self.ends_at, ends_at__gt=self.starts_at
        )
        if self.pk:
            overlap = overlap.exclude(pk=self.pk)
        if overlap.exists():
            raise ValidationError("На эти даты уже есть другая включённая акция. Оставьте одну.")


class PreorderRelease(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Запланирован"
        SELLING = "selling", "Идут продажи"
        CLOSED = "closed", "Продажи закрыты"
        RELEASED = "released", "Файлы разосланы"
        FAILED = "failed", "Нет файла к дате"

    product = models.OneToOneField(
        "catalog.Product",
        verbose_name="Мастер-класс",
        on_delete=models.CASCADE,
        related_name="preorder",
    )
    sales_start = models.DateTimeField("Начало продаж")
    sales_end = models.DateTimeField("Конец продаж")
    release_date = models.DateTimeField(
        "Дата файла", help_text="Эту дату видит покупатель: «файл придёт …»."
    )
    discount_percent = models.PositiveSmallIntegerField(
        "Скидка предзаказа, %", default=0, help_text="0 — без скидки, только бейдж «Предзаказ»."
    )
    status = models.CharField(
        "Статус", max_length=16, choices=Status.choices, default=Status.SCHEDULED
    )
    released_at = models.DateTimeField("Разослан", null=True, blank=True)

    class Meta:
        verbose_name = "предзаказ"
        verbose_name_plural = "предзаказы"
        constraints = [
            models.CheckConstraint(
                condition=Q(discount_percent__lte=90), name="preorder_percent_le_90"
            ),
            models.CheckConstraint(
                condition=Q(sales_end__gt=F("sales_start")), name="preorder_window"
            ),
        ]

    def __str__(self) -> str:
        return f"Предзаказ «{self.product}»"

    def clean(self):
        super().clean()
        if self.sales_start and self.sales_end and self.sales_end <= self.sales_start:
            raise ValidationError({"sales_end": "Конец продаж должен быть позже начала."})
        if self.discount_percent is not None and self.discount_percent > 90:
            raise ValidationError({"discount_percent": "Не больше 90%."})
