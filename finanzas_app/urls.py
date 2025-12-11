# finanzas_app/urls.py

from django.urls import path
from . import views

app_name = "finanzas_app"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    
    # Cuentas financieras
    path("cuentas/", views.cuentas_listado, name="cuentas_listado"),
    path("cuentas/nueva/", views.cuenta_crear, name="cuenta_crear"),
    path("cuentas/<int:pk>/editar/", views.cuenta_editar, name="cuenta_editar"),
    path("cuentas/<int:pk>/toggle/", views.cuenta_toggle, name="cuenta_toggle"),
    
    # Movimientos
    path("movimientos/", views.movimientos_listado, name="movimientos_listado"),
    path("movimientos/nuevo/", views.movimiento_crear, name="movimiento_crear"),
    
    # Ingresos (formulario especializado)
    path("ingresos/nuevo/", views.ingreso_crear, name="ingreso_crear"),
]