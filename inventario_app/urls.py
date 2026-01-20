from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    path("", views.dashboard, name="inicio"),

    # Recursos
    path("recursos/", views.recursos_lista, name="recursos_lista"),
    path("recursos/nuevo/", views.recurso_nuevo, name="recurso_nuevo"),
    path("recursos/<int:pk>/", views.recurso_detalle, name="recurso_detalle"),
    path("recursos/<int:pk>/editar/", views.recurso_editar, name="recurso_editar"),

    # Movimientos
    path("movimientos/", views.movimientos_lista, name="movimientos_lista"),
    path("movimientos/nuevo/", views.movimiento_nuevo, name="movimiento_nuevo"),

    # Categorías
    path("categorias/", views.categorias_lista, name="categorias_lista"),
    path("categorias/nueva/", views.categoria_nueva, name="categoria_nueva"),

    # Ubicaciones
    path("ubicaciones/", views.ubicaciones_lista, name="ubicaciones_lista"),
    path("ubicaciones/nueva/", views.ubicacion_nueva, name="ubicacion_nueva"),
    path("ubicaciones/<int:pk>/editar/", views.ubicacion_editar, name="ubicacion_editar"),

    # Reportes
    path("reportes/", views.reportes, name="reportes"),
    # Ayuda / Guías

    path("ayuda/depreciacion/", views.ayuda_depreciacion, name="ayuda_depreciacion"),

]