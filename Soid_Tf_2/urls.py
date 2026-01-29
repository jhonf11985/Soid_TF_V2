from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from core import ajax_views
from django.views.generic import TemplateView


urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔐 Rutas de autenticación (login, logout, cambio de contraseña, etc.)
    path("accounts/", include("django.contrib.auth.urls")),

    # Ruta principal (home)
    path("", include("core.urls")),

    # Ruta del módulo Miembros
    path("miembros/", include("miembros_app.urls")),

    path("notificaciones/", include("notificaciones_app.urls")),
    path("votacion/", include("votacion_app.urls")),

    path("finanzas/", include("finanzas_app.urls")),
    
    # 👇 API para búsqueda de miembros (usado por autocomplete)
    path("api/buscar-miembros/", ajax_views.buscar_miembros, name="buscar_miembros"),
    path("estructura/", include("estructura_app.urls")),

    path("nuevo-creyente/", include("nuevo_creyente_app.urls")),

    path(
        "actualizacion-datos/",
        include("actualizacion_datos_miembros.urls")
    ),
    
    # ✅ Service Worker en raíz
    path(
        "sw.js",
        TemplateView.as_view(
            template_name="sw.js",
            content_type="application/javascript",
        ),
        name="sw",
    ),
    
    # ✅ Manifest en raíz (IMPORTANTE para PWA)
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

    path('evaluaciones/', include('evaluaciones_app.urls', namespace='evaluaciones_app')),
    path("docs/", include("core.urls_docs", namespace="docs")),

]

# Para servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)