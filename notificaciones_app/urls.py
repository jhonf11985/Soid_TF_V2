from django.urls import path
from . import views

app_name = "notificaciones_app"

urlpatterns = [
    path("marcar-leidas/", views.marcar_todas_leidas, name="marcar_todas_leidas"),
]
