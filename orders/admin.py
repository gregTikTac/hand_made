"""Orders are created by checkout. The author looks at them; prices are a snapshot and stay read-only."""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from core.money import format_rub
from orders.models import Order, OrderItem


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("title", "unit_price_rub", "price_source", "product")
    readonly_fields = fields

    @admin.display(description="Цена")
    def unit_price_rub(self, obj):
        return format_rub(obj.unit_price)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ("number", "email", "status", "total_rub", "marketing_consent", "created_at")
    list_filter = ("status", "marketing_consent")
    search_fields = ("number", "email")
    readonly_fields = (
        "id",
        "number",
        "email",
        "status",
        "subtotal",
        "discount_total",
        "total",
        "consent_offer_at",
        "consent_pdn_at",
        "offer_version",
        "pdn_version",
        "marketing_consent",
        "ip",
        "user_agent",
        "created_at",
        "updated_at",
        "paid_at",
    )
    inlines = (OrderItemInline,)

    def has_add_permission(self, request):
        return False

    @admin.display(description="К оплате", ordering="total")
    def total_rub(self, obj):
        return format_rub(obj.total)
