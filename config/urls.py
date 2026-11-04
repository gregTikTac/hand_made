"""URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from catalog.sitemaps import ProductSitemap
from pages import views

sitemaps = {"products": ProductSitemap}

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", views.home, name="home"),
    path("info/<slug:slug>/", views.page, name="page"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", views.robots, name="robots"),
    path("", include("catalog.urls")),
    path("", include("orders.urls")),
    path("", include("delivery.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
