"""Guest orders. Prices on OrderItem are a snapshot taken at checkout, not a live lookup."""

import uuid

from django.db import models

from catalog.pricing import SOURCE_BASE, SOURCE_CAMPAIGN, SOURCE_PREORDER
from core.fields import KopecksField

# Bumped when the offer / privacy text changes (real texts arrive in stage 7).
OFFER_VERSION = "draft-1"
PDN_VERSION = "draft-1"


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Создан"
        PENDING = "pending", "Ожидает оплаты"
        PAID = "paid", "Оплачен"
        FULFILLED = "fulfilled", "Файлы отправлены"
        AWAITING_RELEASE = "awaiting_release", "Ждёт выпуска предзаказа"
        CANCELED = "canceled", "Отменён"
        EXPIRED = "expired", "Истёк"
        REFUNDED = "refunded", "Возврат"
        NEEDS_REVIEW = "needs_review", "Нужна проверка"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField("Номер", max_length=20, unique=True)
    email = models.EmailField("Email", db_index=True)
    status = models.CharField(
        "Статус", max_length=20, choices=Status.choices, default=Status.CREATED
    )
    subtotal = KopecksField("Сумма без скидки")
    discount_total = KopecksField("Скидка")
    total = KopecksField("К оплате")
    consent_offer_at = models.DateTimeField("Согласие с офертой")
    consent_pdn_at = models.DateTimeField("Согласие на обработку ПДн")
    offer_version = models.CharField("Версия оферты", max_length=32)
    pdn_version = models.CharField("Версия согласия на ПДн", max_length=32)
    marketing_consent = models.BooleanField("Согласие на рассылку", default=False)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("Браузер", max_length=400, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    paid_at = models.DateTimeField("Оплачен", null=True, blank=True)

    class Meta:
        verbose_name = "заказ"
        verbose_name_plural = "заказы"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.number


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "catalog.Product",
        verbose_name="Мастер-класс",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    title = models.CharField("Название на момент покупки", max_length=200)
    unit_price = KopecksField("Цена")
    price_source = models.CharField(
        "Откуда цена",
        max_length=16,
        choices=(
            (SOURCE_BASE, "Обычная цена"),
            (SOURCE_CAMPAIGN, "Акция"),
            (SOURCE_PREORDER, "Предзаказ"),
        ),
    )
    # Filled in stage 6, when DiscountCampaign exists. No FK yet: the model is not there.
    campaign_id = models.PositiveIntegerField("Акция", null=True, blank=True)

    class Meta:
        verbose_name = "позиция заказа"
        verbose_name_plural = "позиции заказа"
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="orderitem_one_product")
        ]

    def __str__(self) -> str:
        return self.title
