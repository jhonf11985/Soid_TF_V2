from django.urls import path
from . import views

app_name = "nuevo_creyente_app"

urlpatterns = [
    path("", views.dashboard, name="nuevo_creyente"),                 # dashboard del módulo
    path("seguimiento/", views.seguimiento_lista, name="seguimiento_lista"),  # ✅ la lista
]
