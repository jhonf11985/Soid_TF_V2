from django.urls import path
from visitas_app.views import (
    registro_list,
    registro_create,
    registro_detail,
    registro_cerrar,
    registro_reabrir,
    visita_create_en_registro,
    visita_buscar_ajax,
    # Reporte
    reporte_visitas,
    reporte_visitas_pdf,
)

app_name = "visitas_app"

urlpatterns = [
    # Registros
    path("", registro_list, name="registro_list"),
    path("registros/nuevo/", registro_create, name="registro_create"),
    path("registros/<int:pk>/", registro_detail, name="registro_detail"),
    path("registros/<int:registro_id>/agregar-visita/", visita_create_en_registro, name="visita_create_en_registro"),
    path("registros/<int:pk>/cerrar/", registro_cerrar, name="registro_cerrar"),
    path("registros/<int:pk>/reabrir/", registro_reabrir, name="registro_reabrir"),
    
    # AJAX
    path("ajax/buscar/", visita_buscar_ajax, name="visita_buscar_ajax"),
    
    # Reportes
    path("reporte/", reporte_visitas, name="reporte_visitas"),
    path("reporte/pdf/", reporte_visitas_pdf, name="reporte_visitas_pdf"),
]