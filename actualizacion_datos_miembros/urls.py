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
]
