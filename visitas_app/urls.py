from django.urls import path
from visitas_app.views import (
    registro_list,
    registro_create,
    registro_detail,
    registro_cerrar,
    visita_create_en_registro,
    visita_buscar_ajax,
)

app_name = "visitas_app"

urlpatterns = [
    path("", registro_list, name="registro_list"),
    path("registros/nuevo/", registro_create, name="registro_create"),
    path("registros/<int:pk>/", registro_detail, name="registro_detail"),
    path("registros/<int:registro_id>/agregar-visita/", visita_create_en_registro, name="visita_create_en_registro"),
    path("ajax/buscar/", visita_buscar_ajax, name="visita_buscar_ajax"),
    path("registros/<int:pk>/cerrar/", registro_cerrar, name="registro_cerrar"),
]