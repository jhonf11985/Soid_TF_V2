from django.urls import path
from . import views

app_name = "nuevo_creyente_app"

urlpatterns = [
    path("", views.dashboard, name="nuevo_creyente"),
    path("seguimiento/", views.seguimiento_lista, name="seguimiento_lista"),
    path("seguimiento/<int:miembro_id>/", views.seguimiento_detalle, name="seguimiento_detalle"),

    # Ciclo (etapas) y cierre
    path("seguimiento/<int:miembro_id>/set-etapa/", views.seguimiento_set_etapa, name="seguimiento_set_etapa"),
    path("seguimiento/<int:miembro_id>/cerrar/", views.seguimiento_cerrar, name="seguimiento_cerrar"),

    # Padres espirituales
    path("seguimiento/<int:miembro_id>/padre/add/", views.seguimiento_padre_add, name="seguimiento_padre_add"),
    path("seguimiento/<int:miembro_id>/padre/<int:padre_id>/remove/", views.seguimiento_padre_remove, name="seguimiento_padre_remove"),
]
