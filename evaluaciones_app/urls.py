from django.urls import path
from . import views

app_name = "evaluaciones"


urlpatterns = [
    path("", views.mis_unidades, name="dashboard"),
    path("mis-unidades/", views.mis_unidades, name="mis_unidades"),
    path("unidad/<int:unidad_id>/evaluar/", views.evaluar_unidad, name="evaluar_unidad"),
    path("unidad/<int:unidad_id>/perfil/", views.perfil_evaluacion_unidad, name="perfil_evaluacion_unidad"),
    path("api/guardar-miembro/", views.guardar_evaluacion_miembro, name="guardar_evaluacion_miembro"),
    path("unidad/<int:evaluacion_id>/resultados/", views.ver_resultados_unidad, name="ver_resultados_unidad"),
    path("evaluacion/<int:evaluacion_id>/cerrar/", views.cerrar_evaluacion_unidad, name="cerrar_evaluacion_unidad"),
    path("evaluacion/<int:evaluacion_id>/reabrir/", views.reabrir_evaluacion_unidad, name="reabrir_evaluacion_unidad"),
    
    # ✅ Modo libre
    path("unidad/<int:unidad_id>/evaluaciones/", views.listar_evaluaciones_unidad, name="listar_evaluaciones_unidad"),
    path("unidad/<int:unidad_id>/nueva-evaluacion/", views.crear_nueva_evaluacion_libre, name="crear_nueva_evaluacion_libre"),
    path("unidad/<int:unidad_id>/evaluar/<int:evaluacion_id>/", views.evaluar_unidad, name="evaluar_unidad_especifica"),
]