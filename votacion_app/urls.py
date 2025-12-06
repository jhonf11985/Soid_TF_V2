from django.urls import path
from . import views

app_name = "votacion"

urlpatterns = [
    # Lista
    path("", views.lista_votaciones, name="lista_votaciones"),

    # Configuración
    path("nueva/", views.crear_votacion, name="crear_votacion"),
    path("configurar/<int:pk>/", views.editar_votacion, name="editar_votacion"),
    path(
        "configurar/<int:pk>/nueva_ronda/",
        views.agregar_ronda,
        name="agregar_ronda"
    ),
    path("duplicar/<int:pk>/", views.duplicar_votacion, name="duplicar_votacion"),

    # Flujo kiosko
    path("kiosko/", views.kiosko_ingreso_codigo, name="kiosko_ingreso_codigo"),
    path("kiosko/seleccionar/", views.kiosko_seleccion_candidato, name="kiosko_seleccion_candidato"),
    path("kiosko/confirmacion/", views.kiosko_confirmacion, name="kiosko_confirmacion"),

    # Eliminar
    path("eliminar/<int:pk>/", views.eliminar_votacion, name="eliminar_votacion"),
    path(
        "configurar/<int:pk>/candidatos/",
        views.gestionar_candidatos,
        name="gestionar_candidatos"
    ),
    path(
    "documentacion/",
    views.documentacion_sistemas_votacion,
   name="documentacion_sistemas_votacion",
),
    path("kiosko/confirmar/", views.kiosko_confirmacion_identidad, name="kiosko_confirmacion_identidad"),
    path(
    "kiosko/voto-exitoso/",
    views.kiosko_voto_exitoso,
    name="kiosko_voto_exitoso",
),
    path(
        "pantalla/",
        views.pantalla_votacion_actual,
        name="pantalla_votacion_actual",
    ),


]
