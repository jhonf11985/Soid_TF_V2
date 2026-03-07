from django.urls import path

from .views import carpeta_create, carpeta_list, dashboard_documentos, documento_list
from documentos_app.views import documentos, carpetas
app_name = "documentos_app"

urlpatterns = [
    path("", dashboard_documentos, name="dashboard"),
    path("carpetas/", carpeta_list, name="carpeta_list"),
    path("carpetas/nueva/", carpeta_create, name="carpeta_create"),
    path("documentos/", documento_list, name="documento_list"),
    path("carpetas/nueva/", carpetas.carpeta_create, name="carpeta_create"),
]