"""Catalog models: Category, Product, ProductImage, ProductVideo (ARCHITECTURE §2).

Money is stored as integer kopecks. Prices shown to customers come ONLY from
``catalog.pricing.get_price`` — never read ``base_price`` directly in templates.
"""

import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.urls import reverse

from catalog import images as image_utils
from catalog.validators import (
    validate_image_extension,
    validate_image_size,
    validate_pdf_extension,
    validate_pdf_header,
)
from catalog.video import (
    PROVIDER_RUTUBE,
    PROVIDER_VK,
    PROVIDER_YOUTUBE,
    VideoUrlError,
    parse_video_url,
)
from core.fields import KopecksField
from core.storage import get_private_storage
from core.text import unique_slug


def upload_product_image(instance, filename: str) -> str:
    """Random file name: no clashes, no Cyrillic/space problems, no leaking of source names."""
    return f"products/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def upload_materials_image(instance, filename: str) -> str:
    return f"materials/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def upload_product_pdf(instance, filename: str) -> str:
    return f"pdf/{uuid.uuid4().hex}.pdf"


class Category(models.Model):
    """Product category. «Все мастер-классы» is virtual; «Комбо» is ``Product.is_combo``."""

    title = models.CharField("Название", max_length=100)
    slug = models.SlugField("Адрес (slug)", max_length=120, unique=True, blank=True)
    position = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_visible = models.BooleanField("Показывать на сайте", default=True)

    class Meta:
        verbose_name = "категория"
        verbose_name_plural = "категории"
        ordering = ("position", "title")

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Category, self.title, max_length=120, exclude_pk=self.pk)
        super().save(*args, **kwargs)


class ProductQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Product.Status.PUBLISHED)

    def combos(self):
        return self.filter(is_combo=True)

    def with_images(self):
        """Prefetch images cover-first, so ``product.cover`` costs no extra queries."""
        return self.prefetch_related(
            models.Prefetch(
                "images", queryset=ProductImage.objects.order_by("-is_cover", "position", "id")
            )
        )


class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликован"
        ARCHIVED = "archived", "В архиве"

    title = models.CharField("Название", max_length=200)
    slug = models.SlugField(
        "Адрес страницы (slug)",
        max_length=220,
        unique=True,
        blank=True,
        help_text="Латиницей, например kozlyonok-borya. Заполняется автоматически из названия.",
    )
    short_description = models.CharField(
        "Короткое описание",
        max_length=300,
        blank=True,
        help_text="Одна-две фразы для поисковиков и соцсетей. Если пусто — берётся начало описания.",
    )
    description = models.TextField(
        "Описание",
        blank=True,
        help_text="Что входит в мастер-класс, размер игрушки, видео, поддержка автора.",
    )
    base_price = KopecksField(
        "Цена, ₽",
        help_text="Обычная цена в рублях, например 450. Скидки и акции считаются автоматически.",
    )
    compare_price = KopecksField(
        "Старая цена, ₽",
        null=True,
        blank=True,
        help_text="Необязательно: зачёркнутая цена без акции. Должна быть больше обычной.",
    )
    categories = models.ManyToManyField(
        Category, verbose_name="Категории", related_name="products", blank=True
    )
    is_combo = models.BooleanField(
        "Комбо",
        default=False,
        help_text="Набор из нескольких игрушек. Такие товары показываются на вкладке «Комбо».",
    )
    status = models.CharField(
        "Статус",
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Только «Опубликован» виден покупателям.",
    )

    height_cm = models.PositiveSmallIntegerField("Высота, см", null=True, blank=True)
    length_cm = models.PositiveSmallIntegerField("Длина, см", null=True, blank=True)
    construction = models.CharField(
        "Особенности вязания",
        max_length=300,
        blank=True,
        help_text="Например: цельно вязаная, пришиваем ушки и мордочку.",
    )
    clothing_included = models.BooleanField("В мастер-класс входит одежда", default=False)
    videos_count = models.PositiveSmallIntegerField(
        "Видео внутри мастер-класса",
        default=0,
        help_text="Сколько видео сложных моментов входит в мастер-класс (число для описания).",
    )

    materials_image = models.ImageField(
        "Необходимые материалы (фото)",
        upload_to=upload_materials_image,
        width_field="materials_image_width",
        height_field="materials_image_height",
        blank=True,
        validators=[validate_image_extension, validate_image_size],
        help_text="Фотография со всеми материалами (пряжа, крючок, наполнитель), а не список текстом.",
    )
    materials_image_width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    materials_image_height = models.PositiveIntegerField(null=True, blank=True, editable=False)

    pdf_file = models.FileField(
        "PDF мастер-класса",
        upload_to=upload_product_pdf,
        storage=get_private_storage,
        null=True,
        blank=True,
        validators=[validate_pdf_extension, validate_pdf_header],
        help_text="Файл хранится в закрытом хранилище и отдаётся только покупателям.",
    )

    sort_order = models.PositiveIntegerField(
        "Порядок в каталоге", default=0, help_text="Меньше число — выше в каталоге."
    )
    popularity = models.PositiveIntegerField(
        "Популярность",
        default=0,
        help_text="Чем больше число, тем выше в блоке «Популярные» на главной.",
    )
    seo_title = models.CharField("SEO-заголовок", max_length=200, blank=True)
    seo_description = models.CharField("SEO-описание", max_length=300, blank=True)

    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Изменён", auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "мастер-класс"
        verbose_name_plural = "мастер-классы"
        ordering = ("sort_order", "-created_at", "id")
        indexes = [
            models.Index(fields=["status", "sort_order"], name="product_status_sort_idx"),
            models.Index(fields=["status", "is_combo"], name="product_status_combo_idx"),
            models.Index(fields=["status", "-popularity"], name="product_status_pop_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(base_price__gt=0), name="product_base_price_gt_0"),
            models.CheckConstraint(
                condition=Q(compare_price__isnull=True) | Q(compare_price__gt=0),
                name="product_compare_price_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("catalog:product", kwargs={"slug": self.slug})

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED

    @property
    def cover(self):
        """Cover image: the one flagged ``is_cover``, otherwise the first by position."""
        images = list(self.images.all())  # uses the prefetch cache when available
        if not images:
            return None
        flagged = [image for image in images if image.is_cover]
        if flagged:
            return flagged[0]
        return min(images, key=lambda image: (image.position, image.pk))

    @property
    def card_description(self) -> str:
        """Short text for meta description / cards."""
        return self.short_description or self.description[:160]

    def clean(self):
        super().clean()
        errors = {}
        if (
            self.compare_price is not None
            and self.base_price is not None
            and self.compare_price <= self.base_price
        ):
            errors["compare_price"] = (
                "Старая цена должна быть больше обычной (или оставьте поле пустым)."
            )
        if self.status == self.Status.PUBLISHED and not self.pdf_file and not self.is_combo:
            # Stage 6 relaxes this for preorders (PreorderRelease); combos deliver their items' PDFs.
            errors["pdf_file"] = (
                "Нельзя опубликовать мастер-класс без PDF: покупатель оплатит и не получит файл. "
                "Загрузите PDF или оставьте черновик."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Product, self.title, max_length=220, exclude_pk=self.pk)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "slug"}
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, verbose_name="Мастер-класс", on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        "Фото",
        upload_to=upload_product_image,
        width_field="image_width",
        height_field="image_height",
        validators=[validate_image_extension, validate_image_size],
        help_text="Вертикальное фото 4:5 смотрится лучше всего. Форматы: JPG, PNG, WebP.",
    )
    image_width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    image_height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    alt = models.CharField("Описание фото", max_length=200, blank=True)
    position = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_cover = models.BooleanField(
        "Обложка",
        default=False,
        help_text="Главное фото в каталоге. Если не выбрано — первое по порядку.",
    )

    class Meta:
        verbose_name = "фото"
        verbose_name_plural = "фото"
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["product"], condition=Q(is_cover=True), name="productimage_one_cover"
            )
        ]

    def __str__(self) -> str:
        return f"{self.product_id}: {self.image.name}"

    @property
    def srcset(self) -> str:
        return image_utils.srcset(self.image, self.image_width)

    def save(self, *args, **kwargs):
        previous = None
        if self.pk:
            previous = ProductImage.objects.filter(pk=self.pk).only("image", "image_width").first()
        is_new_file = bool(self.image) and not getattr(self.image, "_committed", True)
        with transaction.atomic():
            if self.is_cover and self.product_id:
                # Only one cover per product: demote the others instead of failing on the constraint.
                ProductImage.objects.filter(product_id=self.product_id, is_cover=True).exclude(
                    pk=self.pk
                ).update(is_cover=False)
            super().save(*args, **kwargs)
        if is_new_file:
            if previous and previous.image and previous.image.name != self.image.name:
                image_utils.delete_variants(previous.image, previous.image_width)
                previous.image.delete(save=False)
            image_utils.generate_variants(self.image)


class ProductVideo(models.Model):
    """Video by link (VK Видео / Rutube / YouTube); own video files are v2."""

    class Provider(models.TextChoices):
        VK = PROVIDER_VK, "VK Видео"
        RUTUBE = PROVIDER_RUTUBE, "Rutube"
        YOUTUBE = PROVIDER_YOUTUBE, "YouTube"

    product = models.ForeignKey(
        Product, verbose_name="Мастер-класс", on_delete=models.CASCADE, related_name="videos"
    )
    provider = models.CharField("Сервис", max_length=10, choices=Provider.choices, editable=False)
    url = models.URLField(
        "Ссылка на видео",
        max_length=300,
        help_text="Ссылка на видео из VK Видео, Rutube или YouTube — просто скопируйте из адресной строки.",
    )
    title = models.CharField("Подпись", max_length=120, blank=True)
    position = models.PositiveIntegerField("Порядок", default=0, db_index=True)

    class Meta:
        verbose_name = "видео"
        verbose_name_plural = "видео"
        ordering = ("position", "id")

    def __str__(self) -> str:
        return self.title or self.url

    def clean(self):
        super().clean()
        try:
            parsed = parse_video_url(self.url)
        except VideoUrlError as exc:
            raise ValidationError({"url": str(exc)}) from exc
        self.provider = parsed.provider

    def save(self, *args, **kwargs):
        # Always re-detect: the URL may have been edited. Raises VideoUrlError on bad data.
        self.provider = parse_video_url(self.url).provider
        super().save(*args, **kwargs)

    @property
    def embed_url(self) -> str | None:
        """Safe iframe URL, or None if the stored link is no longer recognised."""
        try:
            return parse_video_url(self.url).embed_url
        except VideoUrlError:
            return None
