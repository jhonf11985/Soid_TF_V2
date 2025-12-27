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
    path("asignacion/remover/", views.asignacion_remover, name="asignacion_remover"),

    
    path("unidades/<int:pk>/actividades/", views.unidad_actividades, name="unidad_actividades"),
    path("unidades/<int:pk>/actividades/nueva/", views.actividad_crear, name="actividad_crear"),

    path("unidades/<int:pk>/reportes/", views.unidad_reportes, name="unidad_reportes"),
    path("unidades/<int:pk>/reportes/<int:anio>/<int:mes>/imprimir/", views.reporte_unidad_imprimir, name="reporte_unidad_imprimir"),
        # ✅ editar usando el mismo template del crear
    path("roles/<int:rol_id>/editar/", views.rol_editar, name="rol_editar"),
    path(
    "unidades/<int:pk>/reportes/padron/<int:anio>/<int:mes>/imprimir/",
    views.reporte_unidad_padron_imprimir,
    name="reporte_unidad_padron_imprimir"
    ),
    path(
    "unidades/<int:pk>/reportes/liderazgo/imprimir/",
    views.reporte_unidad_liderazgo_imprimir,
    name="reporte_unidad_liderazgo_imprimir",
),
    path(
        "unidades/<int:pk>/reportes/actividades/imprimir/",
        views.reporte_unidad_actividades_imprimir,
        name="reporte_unidad_actividades_imprimir",
    ),

]
