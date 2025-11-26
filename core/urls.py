from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Página de inicio del sistema
    path("", views.home, name="home"),

    # Menú principal de configuración
    path("configuracion/", views.configuracion_sistema, name="configuracion"),

    # Secciones de configuración
    path("configuracion/general/", views.configuracion_general, name="configuracion_general"),
    path("configuracion/contacto/", views.configuracion_contacto, name="configuracion_contacto"),
    path("configuracion/reportes/", views.configuracion_reportes, name="configuracion_reportes"),
]
