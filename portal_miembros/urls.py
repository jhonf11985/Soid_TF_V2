from django.urls import path
from . import views

app_name = "portal_miembros"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("perfil/", views.perfil, name="perfil"),
    path("notificaciones/", views.notificaciones, name="notificaciones"),
]
