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
]
