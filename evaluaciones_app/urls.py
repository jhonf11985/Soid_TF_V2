from django.urls import path
from . import views

app_name = 'evaluaciones'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('mis-unidades/', views.mis_unidades, name='mis_unidades'),
    path('unidad/<int:unidad_id>/', views.unidad_miembros, name='unidad_miembros'),
    path('unidad/<int:unidad_id>/miembro/<int:miembro_id>/evaluar/', views.evaluar_miembro, name='evaluar_miembro'),
]
