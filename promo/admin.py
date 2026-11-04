from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from promo.models import DiscountCampaign, PreorderRelease
from promo.services import release_preorder


@admin.register(DiscountCampaign)
class DiscountCampaignAdmin(ModelAdmin):
    list_display = ("title", "percent", "starts_at", "ends_at", "is_active", "exclude_preorders")
    list_filter = ("is_active",)
    search_fields = ("title",)


@admin.register(PreorderRelease)
class PreorderReleaseAdmin(ModelAdmin):
    list_display = (
        "product",
        "status",
        "discount_percent",
        "sales_start",
        "sales_end",
        "release_date",
    )
    list_filter = ("status",)
    autocomplete_fields = ("product",)
    actions = ("release_now",)

    @admin.action(description="Выпустить: разослать PDF тем, кто уже оплатил")
    def release_now(self, request, queryset):
        sent = 0
        for release in queryset:
            sent += release_preorder(release.pk)
        self.message_user(request, f"Писем поставлено: {sent}.", messages.SUCCESS)
