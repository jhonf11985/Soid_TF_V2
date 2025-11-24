from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path("admin/", admin.site.urls),

    # Ruta principal (home)
    path("", include("core.urls")),

    # Ruta del módulo Miembros
    path("miembros/", include("miembros_app.urls")),
]

# Para servir fotos y archivos subidos
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)