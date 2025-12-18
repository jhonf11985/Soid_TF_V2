from django.urls import path
from . import views

app_name = "estructura_app"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("unidades/nueva/", views.unidad_crear, name="unidad_crear"),
       path('unidades/<int:pk>/', views.unidad_detalle, name='unidad_detalle'),
        path('unidades/', views.unidad_listado, name='unidad_listado'),
]
