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
 # Ciclos
path("ciclos/nuevo/", views.ciclo_crear, name="ciclo_crear"),
path("ciclos/<int:pk>/editar/", views.ciclo_editar, name="ciclo_editar"),

  # ✅ LISTA DE GRUPOS
    path("grupos/", views.grupos_listado, name="grupos"),
     path('grupos/reporte/', views.grupos_reporte, name='grupos_reporte'), 
         path(
        "grupos/<int:grupo_id>/sesion/abrir/",
        views.grupo_sesion_abrir,
        name="grupo_sesion_abrir",
    ),
    
path("sesiones/<int:sesion_id>/", views.sesion_detalle, name="sesion_detalle"),
path("sesiones/<int:sesion_id>/kiosko/", views.sesion_kiosko, name="sesion_kiosko"),
path("sesiones/<int:sesion_id>/kiosko/marcar/", views.sesion_kiosko_marcar, name="sesion_kiosko_marcar"),
path("sesiones/<int:sesion_id>/cerrar/", views.sesion_cerrar, name="sesion_cerrar"),
path("roles/", views.roles_formativos, name="roles_formativos"),
path("roles/", views.roles_formativos, name="roles_formativos"),

path("roles/nuevo/", views.rol_formativo_nuevo, name="rol_formativo_nuevo"),
path("roles/<int:pk>/toggle/", views.rol_formativo_toggle, name="rol_formativo_toggle"),


]