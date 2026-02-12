from django.urls import path
from . import views

app_name = "ejecutivo_app"

urlpatterns = [
    path("", views.inicio, name="dashboard"),          # Inicio Ejecutivo (Resumen)
    path("personas/", views.personas, name="personas"),# Placeholder (Nivel 2 luego)
]
