
from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("", views.dashboard, name="inicio"),  # alias para evitar NoReverseMatch

    # Placeholders para que el sidebar no rompa
    path("recursos/", views.recursos_lista, name="recursos_lista"),
    path("recursos/nuevo/", views.recurso_nuevo, name="recurso_nuevo"),

    path("movimientos/", views.movimientos_lista, name="movimientos_lista"),
    path("movimientos/nuevo/", views.movimiento_nuevo, name="movimiento_nuevo"),

    path("categorias/", views.categorias_lista, name="categorias_lista"),
    path("ubicaciones/", views.ubicaciones_lista, name="ubicaciones_lista"),

    path("reportes/", views.reportes, name="reportes"),
]

