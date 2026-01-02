from django.urls import path
from . import views

app_name = "nuevo_creyente_app"

urlpatterns = [
    path("", views.dashboard, name="nuevo_creyente"),                 # dashboard del módulo
    path("seguimiento/", views.seguimiento_lista, name="seguimiento_lista"),  # ✅ la lista
     path("seguimiento/<int:miembro_id>/", views.seguimiento_detalle, name="seguimiento_detalle"),
path("seguimiento/<int:miembro_id>/padres/add/", views.seguimiento_padre_add, name="seguimiento_padre_add"),
path("seguimiento/<int:miembro_id>/padres/<int:padre_id>/remove/", views.seguimiento_padre_remove, name="seguimiento_padre_remove"),

]
