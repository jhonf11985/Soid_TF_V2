from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔐 Rutas de autenticación (login, logout, cambio de contraseña, etc.)
    path("accounts/", include("django.contrib.auth.urls")),

    # Ruta principal (home)
    path("", include("core.urls")),

    # Ruta del módulo Miembros
    path("miembros/", include("miembros_app.urls")),

    path("accounts/", include("django.contrib.auth.urls")),

    path("notificaciones/", include("notificaciones_app.urls")),  # 👈 AÑADIDO
    path("votacion/", include("votacion_app.urls")),  # 👈 FALTABA LA COMA AQUÍ

    path("finanzas/", include("finanzas_app.urls")),  # 👈 NUEVA
]

# Para servir fotos y archivos subidos
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
