from django.urls import path
from . import views

app_name = "codigo_qr"

urlpatterns = [
    path("scan/", views.qr_scan, name="scan"),
    path("t/<str:token>/", views.qr_resolver, name="resolver"),
]
