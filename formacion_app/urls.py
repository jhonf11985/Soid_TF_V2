from django.urls import path
from . import views

app_name = "formacion"

urlpatterns = [
    # Dashboard
    path("", views.inicio_formacion, name="inicio"),

    # Programas educativos
    path("programas/", views.programas_list, name="programas"),
    path("programas/nuevo/", views.programa_crear, name="programa_crear"),
    path("programas/<int:pk>/editar/", views.programa_editar, name="programa_editar"),

    # Grupos / Clases
    path("grupos/", views.grupos_listado, name="grupos"),
    path("grupos/nuevo/", views.grupo_crear, name="grupo_crear"),
    path("grupos/<int:pk>/editar/", views.grupo_editar, name="grupo_editar"),
    path("grupos/reporte/", views.grupos_reporte, name="grupos_reporte"),

    # Sesiones
    path("grupos/<int:grupo_id>/sesion/abrir/", views.grupo_sesion_abrir, name="grupo_sesion_abrir"),
    path("sesiones/<int:sesion_id>/", views.sesion_detalle, name="sesion_detalle"),
    path("sesiones/<int:sesion_id>/kiosko/", views.sesion_kiosko, name="sesion_kiosko"),
    path("sesiones/<int:sesion_id>/kiosko/marcar/", views.sesion_kiosko_marcar, name="sesion_kiosko_marcar"),
    path("sesiones/<int:sesion_id>/cerrar/", views.sesion_cerrar, name="sesion_cerrar"),

    # Roles formativos
    path("roles/", views.roles_formativos, name="roles_formativos"),
    path("roles/nuevo/", views.rol_formativo_nuevo, name="rol_formativo_nuevo"),
    path("roles/<int:pk>/toggle/", views.rol_formativo_toggle, name="rol_formativo_toggle"),

    # Reporte programas
    path("reportes/programas/", views.reporte_analisis_programas, name="reporte_programas"),

    # Inicio Maestro
    path("inicio-maestro/", views.inicio_maestro_formacion, name="inicio_maestro"),
    path("mi-clase/<int:grupo_id>/", views.ir_a_mi_clase, name="ir_a_mi_clase"),
    path("grupos/<int:pk>/", views.grupo_detalle, name="grupo_detalle"),

]
