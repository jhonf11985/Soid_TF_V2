from django.urls import path
from . import views

app_name = "actualizacion_datos_miembros"

urlpatterns = [
    # Público (sin login)
    path("<uuid:token>/", views.formulario_publico, name="formulario_publico"),
    path("<uuid:token>/ok/", views.formulario_ok, name="formulario_ok"),

    # Admin (requiere login)
    path("admin/solicitudes/", views.solicitudes_lista, name="solicitudes_lista"),
    path("admin/solicitudes/<int:pk>/", views.solicitud_detalle, name="solicitud_detalle"),
    path("admin/solicitudes/<int:pk>/aplicar/", views.solicitud_aplicar, name="solicitud_aplicar"),
    path("admin/solicitudes/<int:pk>/rechazar/", views.solicitud_rechazar, name="solicitud_rechazar"),

    # Admin: generar/ver link por miembro
    path("admin/generar-link/<int:miembro_id>/", views.generar_link_miembro, name="generar_link_miembro"),
]
