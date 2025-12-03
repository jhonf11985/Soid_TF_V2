from django.urls import path
from . import views

app_name = "votacion"

urlpatterns = [
    # Lista
    path("", views.lista_votaciones, name="lista_votaciones"),

    # Configuración
    path("nueva/", views.crear_votacion, name="crear_votacion"),
    path("configurar/<int:pk>/", views.editar_votacion, name="editar_votacion"),
    path("duplicar/<int:pk>/", views.duplicar_votacion, name="duplicar_votacion"),

    # Flujo kiosko
    path("kiosko/", views.kiosko_ingreso_codigo, name="kiosko_ingreso_codigo"),
    path("kiosko/seleccionar/", views.kiosko_seleccion_candidato, name="kiosko_seleccion_candidato"),
    path("kiosko/confirmacion/", views.kiosko_confirmacion, name="kiosko_confirmacion"),
    path("eliminar/<int:pk>/", views.eliminar_votacion, name="eliminar_votacion"),

]
