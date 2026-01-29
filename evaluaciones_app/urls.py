from django.urls import path
from . import views

app_name = "evaluaciones"

urlpatterns = [
    path("", views.mis_unidades, name="dashboard"),      # /evaluaciones/
    path("mis-unidades/", views.mis_unidades, name="mis_unidades"),
    path("unidad/<int:unidad_id>/evaluar/", views.evaluar_unidad, name="evaluar_unidad"),
        path(
        "unidad/<int:unidad_id>/perfil/",
        views.perfil_evaluacion_unidad,
        name="perfil_evaluacion_unidad",
    ),
 
    # 👇 NUEVA URL para guardar via AJAX
    path('api/guardar-miembro/', views.guardar_evaluacion_miembro, name='guardar_evaluacion_miembro'),
     path("unidad/<int:evaluacion_id>/resultados/", views.ver_resultados_unidad, name="ver_resultados_unidad"),


        path('evaluacion/<int:evaluacion_id>/cerrar/', views.cerrar_evaluacion_unidad, name='cerrar_evaluacion_unidad'),
    path('evaluacion/<int:evaluacion_id>/reabrir/', views.reabrir_evaluacion_unidad, name='reabrir_evaluacion_unidad'),

]
