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
    
    # Categorías de movimiento
    path("categorias/", views.categorias_listado, name="categorias_listado"),
    path("categorias/nueva/", views.categoria_crear, name="categoria_crear"),
    path("categorias/<int:pk>/editar/", views.categoria_editar, name="categoria_editar"),
    path("categorias/<int:pk>/toggle/", views.categoria_toggle, name="categoria_toggle"),
    
    # Movimientos
    path("movimientos/", views.movimientos_listado, name="movimientos_listado"),
    path("movimientos/nuevo/", views.movimiento_crear, name="movimiento_crear"),
    path("movimientos/<int:pk>/editar/", views.movimiento_editar, name="movimiento_editar"),
    path("movimientos/<int:pk>/anular/", views.movimiento_anular, name="movimiento_anular"),
    
    # Ingresos (formulario especializado)
    path("ingresos/nuevo/", views.ingreso_crear, name="ingreso_crear"),
    # Egresos (formulario especializado)
    path("egresos/nuevo/", views.egreso_crear, name="egreso_crear"),

]