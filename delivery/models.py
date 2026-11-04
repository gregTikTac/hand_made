"""Download links and the mail log. The raw token is never stored (ADR-0004)."""

import uuid

from django.db import models

from core.storage import get_private_storage

LINK_DAYS = 30
LINK_DOWNLOADS = 5


class DownloadLink(models.Model):
    order_item = models.ForeignKey(
        "orders.OrderItem",
        verbose_name="Позиция",
        on_delete=models.CASCADE,
        related_name="links",
    )
    label = models.CharField("Название файла", max_length=200)
    token_hash = models.CharField("Хеш ссылки", max_length=64, unique=True)
    watermarked = models.FileField(
        "PDF с пометкой покупателя",
        upload_to="downloads/%Y/%m/",
        storage=get_private_storage,
    )
    expires_at = models.DateTimeField("Действует до")
    max_downloads = models.PositiveSmallIntegerField("Лимит скачиваний", default=LINK_DOWNLOADS)
    download_count = models.PositiveSmallIntegerField("Скачано", default=0)
    revoked = models.BooleanField("Отозвана", default=False)
    last_ip = models.GenericIPAddressField("Последний IP", null=True, blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "ссылка на файл"
        verbose_name_plural = "ссылки на файлы"
        ordering = ("id",)

    def __str__(self) -> str:
        return self.label


class EmailLog(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "В очереди"
        SENT = "sent", "Отправлено"
        FAILED = "failed", "Ошибка"
        BOUNCED = "bounced", "Не доставлено"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order",
        verbose_name="Заказ",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="emails",
    )
    to = models.EmailField("Кому")
    template = models.CharField("Шаблон", max_length=40)
    status = models.CharField(
        "Статус", max_length=16, choices=Status.choices, default=Status.QUEUED
    )
    provider_message_id = models.CharField("ID у почтового сервиса", max_length=200, blank=True)
    attempts = models.PositiveSmallIntegerField("Попытки", default=0)
    error = models.TextField("Ошибка", blank=True)
    dedup_key = models.CharField("Ключ повтора", max_length=80, unique=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "письмо"
        verbose_name_plural = "письма"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.template} → {self.to}"
