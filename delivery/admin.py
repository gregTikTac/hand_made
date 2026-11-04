from django.contrib import admin
from unfold.admin import ModelAdmin

from delivery.models import DownloadLink, EmailLog


@admin.register(DownloadLink)
class DownloadLinkAdmin(ModelAdmin):
    list_display = (
        "label",
        "order_item",
        "download_count",
        "max_downloads",
        "revoked",
        "expires_at",
    )
    list_filter = ("revoked",)
    search_fields = ("label", "order_item__order__number", "order_item__order__email")
    readonly_fields = (
        "order_item",
        "label",
        "token_hash",
        "watermarked",
        "expires_at",
        "max_downloads",
        "download_count",
        "revoked",
        "last_ip",
        "created_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ("created_at", "to", "template", "status", "attempts")
    list_filter = ("status", "template")
    search_fields = ("to", "dedup_key", "order__number")
    readonly_fields = (
        "order",
        "to",
        "template",
        "status",
        "provider_message_id",
        "attempts",
        "error",
        "dedup_key",
        "created_at",
    )

    def has_add_permission(self, request):
        return False
