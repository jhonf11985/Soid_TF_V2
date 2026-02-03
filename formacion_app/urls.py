from django.urls import path
from . import views

app_name = "formacion"

urlpatterns = [
    # Dashboard
    path("", views.inicio_formacion, name="inicio"),
    
    # Programas educativos
    
    path("programas/nuevo/", views.programa_crear, name="programa_crear"),
    path("programas/<int:pk>/editar/", views.programa_editar, name="programa_editar"),
]