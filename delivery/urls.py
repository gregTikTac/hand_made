from django.urls import path

from delivery import views

app_name = "delivery"

urlpatterns = [
    path("d/resend/", views.resend, name="resend"),
    path("d/<str:token>/", views.download, name="download"),
]
