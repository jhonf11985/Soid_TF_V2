from django.urls import path
from . import views

app_name = "portal_miembros"

urlpatterns = [
    # Existentes
    path("", views.dashboard, name="dashboard"),
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/editar/", views.perfil_editar, name="perfil_editar"),
    path("notificaciones/", views.notificaciones, name="notificaciones"),

    # ═══════════════════════════════════════════════════════════════════════════
    # FAMILIA
    # ═══════════════════════════════════════════════════════════════════════════
    path(
        "ajax/buscar-miembros/",
        views.ajax_buscar_miembros_portal,
        name="ajax_buscar_miembros_portal"
    ),
    path(
        "ajax/validar-relacion/",
        views.ajax_validar_relacion,
        name="ajax_validar_relacion"
    ),
    path(
        "familia/crear-hogar/",
        views.crear_mi_hogar,
        name="crear_mi_hogar"
    ),
    path(
        "familia/agregar-relacion/",
        views.agregar_relacion_portal,
        name="agregar_relacion_portal"
    ),
    path(
        "familia/eliminar-relacion/<int:relacion_id>/",
        views.eliminar_relacion_portal,
        name="eliminar_relacion_portal"
    ),
    path(
        "familia/actualizar-nombre/",
        views.actualizar_nombre_hogar,
        name="actualizar_nombre_hogar"
    ),
]