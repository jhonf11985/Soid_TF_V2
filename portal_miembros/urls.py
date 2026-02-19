from django.urls import path
from . import views

app_name = "portal_miembros"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/editar/", views.perfil_editar, name="perfil_editar"),
    path("notificaciones/", views.notificaciones, name="notificaciones"),
]
