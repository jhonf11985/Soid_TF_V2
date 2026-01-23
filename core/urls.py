# core/urls.py
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

    # ✅ Permisos (Roles y permisos por módulo)
    path("configuracion/permisos/", views.configuracion_permisos, name="configuracion_permisos"),

    # ⭐ Probar correo
    path("configuracion/probar-correo/", views.probar_envio_correo, name="probar_envio_correo"),

    # 👥 Usuarios
    path("usuarios/", views.usuarios_listado, name="listado"),
    path("usuarios/crear/", views.crear_usuario, name="crear_usuario"),

    # 👤 Cuenta
    path("cuenta/perfil/", views.perfil_usuario, name="perfil_usuario"),
    path("cuenta/cambiar-contrasena/", views.cambiar_contrasena, name="cambiar_contrasena"),
    path("cuenta/salir/", views.cerrar_sesion, name="logout"),

    # 🔌 AJAX APIs
    path("api/buscar-miembros/", ajax_views.buscar_miembros, name="api_buscar_miembros"),
    path("api/miembro-detalle/<int:miembro_id>/", ajax_views.miembro_detalle, name="api_miembro_detalle"),
path("usuarios/<int:user_id>/editar/", views.editar_usuario, name="editar_usuario"),

    # ✅ VALIDAR EMAIL EN TIEMPO REAL
    path("api/email-disponible/", ajax_views.email_disponible, name="api_email_disponible"),
]
