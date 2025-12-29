from django.urls import path
from . import views, ajax_views

app_name = "core"



urlpatterns = [
    path("", views.root_redirect, name="root_redirect"),
    path("home/", views.home, name="home"),
 



    # Menú principal de configuración
    path("configuracion/", views.configuracion_sistema, name="configuracion"),

    # Secciones de configuración
    path("configuracion/general/", views.configuracion_general, name="configuracion_general"),
    path("configuracion/contacto/", views.configuracion_contacto, name="configuracion_contacto"),
    path("configuracion/reportes/", views.configuracion_reportes, name="configuracion_reportes"),
      # ⭐ Nueva ruta para probar el correo
    path(
        "configuracion/probar-correo/",
        views.probar_envio_correo,
        name="probar_envio_correo",
    ),
    path("usuarios/crear/", views.crear_usuario, name="crear_usuario"),
    
    # 👤 Cuenta de usuario
    path("cuenta/perfil/", views.perfil_usuario, name="perfil_usuario"),
    path("cuenta/cambiar-contrasena/", views.cambiar_contrasena, name="cambiar_contrasena"),
    path("cuenta/salir/", views.cerrar_sesion, name="logout"),
    
    # 🔌 AJAX APIs - Reutilizable en todos los módulos
    path("api/buscar-miembros/", ajax_views.buscar_miembros, name="api_buscar_miembros"),
]