from django.urls import path

from orders import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_page, name="cart"),
    path("cart/add/<int:product_id>/", views.add, name="add"),
    path("cart/remove/<int:product_id>/", views.remove, name="remove"),
    path("cart/checkout/", views.checkout, name="checkout"),
    path("cart/done/", views.done, name="done"),
]
