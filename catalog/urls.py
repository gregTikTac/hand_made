from django.urls import path

from catalog import views

app_name = "catalog"

urlpatterns = [
    path("catalog/", views.catalog_all, name="list"),
    path("catalog/combo/", views.catalog_combo, name="combo"),
    path("p/<slug:slug>/", views.product_detail, name="product"),
]
