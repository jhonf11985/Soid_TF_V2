from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from core import ajax_views
from django.views.generic import TemplateView
from core.views_errors import error_400, error_403, error_404, error_500


urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("core.urls")),
    path("miembros/", include("miembros_app.urls")),
    path("notificaciones/", include("notificaciones_app.urls")),
    path("votacion/", include("votacion_app.urls")),
    path("finanzas/", include("finanzas_app.urls")),
    path("api/buscar-miembros/", ajax_views.buscar_miembros, name="buscar_miembros"),
    path("estructura/", include("estructura_app.urls")),
    path("nuevo-creyente/", include("nuevo_creyente_app.urls")),
    path("actualizacion-datos/", include("actualizacion_datos_miembros.urls")),

    path(
        "sw.js",
        TemplateView.as_view(
            template_name="sw.js",
            content_type="application/javascript",
        ),
        name="sw",
    ),

    path(
        "manifest.json",
        TemplateView.as_view(
            template_name="manifest.json",
            content_type="application/manifest+json",
        ),
        name="manifest",
    ),

    path("inventario/", include("inventario_app.urls")),
    path("agenda/", include("agenda_app.urls")),
    path("evaluaciones/", include("evaluaciones_app.urls", namespace="evaluaciones_app")),
    path("docs/", include("core.urls_docs", namespace="docs")),
    path("codigo-qr/", include("codigo_qr.urls")),
    path("formacion/", include("formacion_app.urls")),
    path("ejecutivo/", include("ejecutivo_app.urls")),
    path("portal/", include("portal_miembros.urls")),
    path("ia/", include("ia_app.urls", namespace="ia_app")),
    path("documentos/", include("documentos_app.urls")),
    path("visitas/", include("visitas_app.urls")),
]

handler400 = error_400
handler403 = error_403
handler404 = error_404
handler500 = error_500


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)