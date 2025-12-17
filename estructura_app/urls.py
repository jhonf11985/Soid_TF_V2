from django.urls import path
from . import views

app_name = "estructura_app"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("unidades/nueva/", views.unidad_crear, name="unidad_crear"),
    path("unidades/<int:pk>/editar/", views.unidad_editar, name="unidad_editar"),
]
