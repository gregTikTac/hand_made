"""Editable texts. Legal pages stay empty until the author writes them."""

from django.db import models


class SiteSettings(models.Model):
    """Single row. Empty fields fall back to the values from the server settings."""

    support_url = models.URLField("Поддержка", blank=True)
    vk_url = models.URLField("VK", blank=True)
    telegram_url = models.URLField("Telegram", blank=True)
    instagram_url = models.URLField("Instagram", blank=True)
    support_email = models.EmailField("Почта поддержки", blank=True)
    legal_name = models.CharField("ФИО в подвале", max_length=200, blank=True)
    banner_text = models.CharField(
        "Текст полоски акции",
        max_length=200,
        blank=True,
        help_text="Если пусто, полоска собирается из включённой акции.",
    )

    class Meta:
        verbose_name = "настройки сайта"
        verbose_name_plural = "настройки сайта"

    def __str__(self) -> str:
        return "Настройки сайта"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        from django.conf import settings

        row, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "support_url": settings.SUPPORT_URL,
                "vk_url": settings.VK_URL,
                "telegram_url": settings.TELEGRAM_URL,
                "instagram_url": settings.INSTAGRAM_URL,
                "legal_name": settings.LEGAL_NAME,
            },
        )
        return row


class Page(models.Model):
    class Slug(models.TextChoices):
        ABOUT = "about", "Об авторе"
        OFFER = "offer", "Публичная оферта"
        PRIVACY = "privacy", "Политика конфиденциальности"
        PDN = "pdn-consent", "Согласие на обработку ПДн"

    slug = models.SlugField("Адрес", unique=True, choices=Slug.choices)
    title = models.CharField("Заголовок", max_length=200)
    body = models.TextField("Текст", blank=True, help_text="Абзацы разделяйте пустой строкой.")
    image = models.ImageField("Фото", upload_to="pages/", blank=True)
    is_published = models.BooleanField(
        "Опубликована",
        default=False,
        help_text="Пока галочка снята, ссылка в подвале никуда не ведёт.",
    )
    updated_at = models.DateTimeField("Изменена", auto_now=True)

    class Meta:
        verbose_name = "страница"
        verbose_name_plural = "страницы"

    def __str__(self) -> str:
        return self.title
