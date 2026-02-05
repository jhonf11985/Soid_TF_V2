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
    

]