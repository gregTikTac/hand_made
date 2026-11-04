"""Orders are created by checkout. The author looks at them; prices are a snapshot and stay read-only."""

from django.conf import settings
from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline

from core.money import format_rub
from orders.models import Order, OrderItem
from orders.services import transition


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
    list_display = ("number", "email", "status", "total_rub", "created_at")
    list_filter = ("status",)
    search_fields = ("number", "email")
    # The newsletter checkbox is gone. Old rows may still have the column; the author does not see it.
    exclude = ("marketing_consent",)
    actions = ("resend_files",)
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
        "ip",
        "user_agent",
        "created_at",
        "updated_at",
        "paid_at",
    )
    inlines = (OrderItemInline,)

    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if settings.DEBUG:
            actions["simulate_payment"] = (
                OrderAdmin.simulate_payment,
                "simulate_payment",
                "Проверка: считать оплаченным и выслать ссылки",
            )
        return actions

    @admin.action(description="Отправить ссылки на PDF ещё раз")
    def resend_files(self, request, queryset):
        from delivery.services import resend_order

        sent = 0
        for order in queryset:
            if resend_order(order.pk):
                sent += 1
        self.message_user(
            request, f"Письма отправлены: {sent} из {queryset.count()}.", messages.SUCCESS
        )

    @admin.action(description="Проверка: считать оплаченным и выслать ссылки")
    def simulate_payment(self, request, queryset):
        """Local only. A real payment must come from the provider, not from this button."""
        if not settings.DEBUG:
            self.message_user(request, "Кнопка доступна только на локальном сайте.", messages.ERROR)
            return
        from delivery.tasks import send_order_files

        for order in queryset:
            if order.status == Order.Status.CREATED:
                transition(order, "pay")
            if order.status == Order.Status.PENDING:
                transition(order, "succeeded")
            send_order_files.delay(str(order.pk))
        self.message_user(
            request, "Оплата имитирована, ссылки поставлены в отправку.", messages.SUCCESS
        )

    @admin.display(description="К оплате", ordering="total")
    def total_rub(self, obj):
        return format_rub(obj.total)
