from django.urls import path
from . import views

app_name = "actualizacion_datos_miembros"

urlpatterns = [
    # ==========================================
    # PÚBLICO - ALTA MASIVA (sin login)
    # ==========================================
    path("alta/", views.alta_publica, name="alta_publica"),
    path("alta/ok/", views.alta_ok, name="alta_ok"),

    # ==========================================
    # PÚBLICO - ACTUALIZACIÓN (sin login)
    # ==========================================
    path("<uuid:token>/", views.formulario_actualizacion_publico, name="formulario_publico"),
    path("<uuid:token>/ok/", views.formulario_ok, name="formulario_ok"),

    # ==========================================
    # ADMIN - ACTUALIZACIÓN (requiere login)
    # ==========================================
    path("admin/solicitudes/", views.solicitudes_lista, name="solicitudes_lista"),
    path("admin/solicitudes/<int:pk>/", views.solicitud_detalle, name="solicitud_detalle"),
    path("admin/solicitudes/<int:pk>/aplicar/", views.solicitud_aplicar, name="solicitud_aplicar"),
    path("admin/solicitudes/<int:pk>/rechazar/", views.solicitud_rechazar, name="solicitud_rechazar"),

    # Admin: generar/ver link por miembro
    path("admin/generar-link/<int:miembro_id>/", views.generar_link_miembro, name="generar_link_miembro"),

    # ==========================================
    # ADMIN - ALTAS MASIVAS (requiere login)
    # ==========================================
    path("admin/altas/", views.altas_lista, name="altas_lista"),
    path("admin/altas/<int:pk>/", views.alta_detalle, name="alta_detalle"),
    path("admin/altas/<int:pk>/aprobar/", views.alta_aprobar, name="alta_aprobar"),
    path("admin/altas/<int:pk>/rechazar/", views.alta_rechazar, name="alta_rechazar"),
    path(
    "admin/altas/<int:pk>/estado-miembro/",
    views.alta_cambiar_estado_miembro,
    name="alta_cambiar_estado_miembro",
),
# Acciones masivas de altas
path("admin/altas/aprobar-masivo/", views.altas_aprobar_masivo, name="altas_aprobar_masivo"),
path("admin/altas/rechazar-masivo/", views.altas_rechazar_masivo, name="altas_rechazar_masivo"),
path("admin/links/", views.links_lista, name="links_lista"),
path("admin/alta-masiva/link/", views.alta_masiva_link, name="alta_masiva_link"),
path("admin/alta-masiva/config/", views.alta_masiva_config, name="alta_masiva_config"),
path("admin/alta-masiva/link/", views.alta_masiva_link, name="alta_masiva_link"),

path("config/actualizacion/", views.actualizacion_config, name="actualizacion_config"),

    # === FAMILIAS (ADMIN) ===
    path("admin/familias/links/", views.familia_links_lista, name="familia_links_lista"),
    path("admin/familias/generar/", views.familia_generar_link, name="generar_link_familia"),
    path("admin/familias/alertas/", views.familia_alertas, name="familia_alertas"),

    # === FAMILIAS (PUBLICO) ===
    path("familia/<uuid:token>/", views.familia_formulario_publico, name="familia_formulario_publico"),

    # === API BUSQUEDA (PUBLICO) ===
    path("api/buscar-miembros/", views.api_buscar_miembros, name="api_buscar_miembros"),

    # === FAMILIAS - SOLICITUDES (ADMIN) ===
    path("admin/familias/solicitudes/", views.familia_solicitudes_lista, name="familia_solicitudes_lista"),
    path("admin/familias/solicitudes/<int:pk>/", views.familia_solicitud_detalle, name="familia_solicitud_detalle"),
    path("admin/familias/solicitudes/<int:pk>/aplicar/", views.familia_solicitud_aplicar, name="familia_solicitud_aplicar"),
    path("admin/familias/solicitudes/<int:pk>/rechazar/", views.familia_solicitud_rechazar, name="familia_solicitud_rechazar"),


]
