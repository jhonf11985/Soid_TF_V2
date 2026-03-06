from django.urls import path

from .views import carpeta_list, dashboard_documentos, documento_list

app_name = "documentos_app"

urlpatterns = [
    path("", dashboard_documentos, name="dashboard"),
    path("carpetas/", carpeta_list, name="carpeta_list"),
    path("documentos/", documento_list, name="documento_list"),
]