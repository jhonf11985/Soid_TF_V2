from django.urls import path
from . import views

app_name = "estructura_app"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # UNIDADES
    path("unidades/", views.unidad_listado, name="unidad_listado"),
    path("unidades/nueva/", views.unidad_crear, name="unidad_crear"),
    path("unidades/<int:pk>/", views.unidad_detalle, name="unidad_detalle"),
    path("unidades/<int:pk>/editar/", views.unidad_editar, name="unidad_editar"),

    # ASIGNACIÓN
    path("asignacion/", views.asignacion_unidad, name="asignacion_unidad"),
    path("asignacion/contexto/", views.asignacion_unidad_contexto, name="asignacion_unidad_contexto"),
    path("asignacion/guardar-contexto/", views.asignacion_guardar_contexto, name="asignacion_guardar_contexto"),

    # ROLES
    path("roles/", views.rol_listado, name="rol_listado"),
    path("roles/nuevo/", views.rol_crear, name="rol_crear"),
    path("asignacion/aplicar/", views.asignacion_aplicar, name="asignacion_aplicar"),

]
