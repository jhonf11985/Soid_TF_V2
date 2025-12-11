from django.urls import path
from . import views

app_name = "finanzas_app"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("movimientos/", views.movimientos_listado, name="movimientos_listado"),
    path("movimientos/nuevo/", views.movimiento_crear, name="movimiento_crear"),
    path("ingresos/nuevo/", views.ingreso_crear, name="ingreso_crear"),
]
