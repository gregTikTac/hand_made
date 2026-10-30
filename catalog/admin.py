"""Django admin for the catalog (django-unfold theme).

The author manages everything here: photos with drag-and-drop ordering and previews,
video links, status/publishing, CSV import/export. Every field has a hint (help_text).
"""

from django.contrib import admin, messages
from django.db import models
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from unfold.decorators import action, display

from catalog.models import Category, Product, ProductImage, ProductVideo
from catalog.pricing import get_price
from catalog.resources import ProductResource
from core.money import format_rub


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 0
    fields = ("preview", "image", "alt", "is_cover", "position")
    readonly_fields = ("preview",)
    ordering_field = "position"  # drag-and-drop sorting
    hide_ordering_field = True
    verbose_name = "фото"
    verbose_name_plural = "Фото (перетаскивайте строки, чтобы поменять порядок)"

    @admin.display(description="Превью")
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:72px;width:58px;object-fit:cover;border-radius:6px">',
            obj.image.url,
        )


class ProductVideoInline(TabularInline):
    model = ProductVideo
    extra = 0
    fields = ("url", "title", "provider_label", "position")
    readonly_fields = ("provider_label",)
    ordering_field = "position"
    hide_ordering_field = True
    verbose_name = "видео"
    verbose_name_plural = "Видео по ссылке (VK Видео, Rutube, YouTube)"
    # A link typed without "https://" is treated as https (Django 6.0 default).
    formfield_overrides = {models.URLField: {"assume_scheme": "https"}}

    @admin.display(description="Сервис")
    def provider_label(self, obj):
        return obj.get_provider_display() if obj.pk else "определится при сохранении"


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("title", "slug", "position", "is_visible")
    list_editable = ("position", "is_visible")
    search_fields = ("title",)
    fields = ("title", "slug", "position", "is_visible")


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_classes = [ProductResource]
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = (
        "cover_preview",
        "title",
        "price_display",
        "status_display",
        "is_combo",
        "has_pdf",
        "sort_order",
    )
    list_display_links = ("cover_preview", "title")
    list_editable = ("sort_order",)
    list_filter = ("status", "is_combo", "categories")
    list_per_page = 50
    search_fields = ("title", "slug", "description")
    filter_horizontal = ("categories",)
    save_on_top = True
    inlines = (ProductImageInline, ProductVideoInline)
    actions = ("publish", "unpublish", "archive")

    fieldsets = (
        (
            "Главное",
            {
                "fields": (
                    "title",
                    "status",
                    "base_price",
                    "compare_price",
                    "is_combo",
                    "categories",
                )
            },
        ),
        ("Описание", {"fields": ("short_description", "description")}),
        (
            "О мастер-классе",
            {
                "fields": (
                    "height_cm",
                    "length_cm",
                    "construction",
                    "clothing_included",
                    "videos_count",
                )
            },
        ),
        ("Необходимые материалы", {"fields": ("materials_image",)}),
        ("Файл для покупателей", {"fields": ("pdf_file",)}),
        (
            "Порядок и поиск",
            {
                "classes": ("collapse",),
                "fields": ("slug", "sort_order", "popularity", "seo_title", "seo_description"),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).with_images()

    @admin.display(description="Фото")
    def cover_preview(self, obj):
        cover = obj.cover
        if not cover:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:56px;width:45px;object-fit:cover;border-radius:6px">',
            cover.image.url,
        )

    @admin.display(description="Цена", ordering="base_price")
    def price_display(self, obj):
        info = get_price(obj)
        if info.has_discount:
            return f"{format_rub(info.final)} (было {format_rub(info.old)})"
        return format_rub(info.final)

    @display(
        description="Статус",
        ordering="status",
        label={
            Product.Status.PUBLISHED.label: "success",
            Product.Status.DRAFT.label: "warning",
            Product.Status.ARCHIVED.label: "info",
        },
    )
    def status_display(self, obj):
        return obj.get_status_display()

    @admin.display(description="PDF", boolean=True)
    def has_pdf(self, obj):
        return bool(obj.pdf_file)

    @action(description="Опубликовать выбранные")
    def publish(self, request, queryset):
        candidates = list(queryset.exclude(status=Product.Status.PUBLISHED))
        blocked = [p for p in candidates if not p.pdf_file and not p.is_combo]
        ok_ids = [p.pk for p in candidates if p not in blocked]
        updated = Product.objects.filter(pk__in=ok_ids).update(status=Product.Status.PUBLISHED)
        if updated:
            self.message_user(request, f"Опубликовано: {updated}.", messages.SUCCESS)
        if blocked:
            self.message_user(
                request,
                "Не опубликованы (нет PDF): " + ", ".join(p.title for p in blocked),
                messages.WARNING,
            )

    @action(description="Снять с публикации (в черновики)")
    def unpublish(self, request, queryset):
        updated = queryset.update(status=Product.Status.DRAFT)
        self.message_user(request, f"Переведено в черновики: {updated}.", messages.SUCCESS)

    @action(description="Отправить в архив")
    def archive(self, request, queryset):
        updated = queryset.update(status=Product.Status.ARCHIVED)
        self.message_user(request, f"Отправлено в архив: {updated}.", messages.SUCCESS)
