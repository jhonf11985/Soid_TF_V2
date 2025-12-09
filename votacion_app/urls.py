from django.urls import path
from . import views

app_name = "votacion"

urlpatterns = [
    # Lista de elecciones
    path("", views.lista_votaciones, name="lista_votaciones"),

    # Configuración de elecciones
    path("nueva/", views.crear_votacion, name="crear_votacion"),
    path("configurar/<int:pk>/", views.editar_votacion, name="editar_votacion"),
    path(
        "configurar/<int:pk>/nueva_ronda/",
        views.agregar_ronda,
        name="agregar_ronda",
    ),
    path("duplicar/<int:pk>/", views.duplicar_votacion, name="duplicar_votacion"),

    # Flujo kiosko
    path("kiosko/", views.kiosko_ingreso_codigo, name="kiosko_ingreso_codigo"),
    path("kiosko/seleccionar/", views.kiosko_seleccion_candidato, name="kiosko_seleccion_candidato"),
    path("kiosko/confirmacion/", views.kiosko_confirmacion, name="kiosko_confirmacion"),
    path("kiosko/confirmar/", views.kiosko_confirmacion_identidad, name="kiosko_confirmacion_identidad"),
    path("kiosko/voto-exitoso/", views.kiosko_voto_exitoso, name="kiosko_voto_exitoso"),

    # Pantallas públicas
    path("pantalla/", views.pantalla_votacion_actual, name="pantalla_votacion_actual"),
    path("pantalla/<int:pk>/", views.pantalla_votacion, name="pantalla_votacion"),

    # Documentación sistemas de votación
    path(
        "documentacion/",
        views.documentacion_sistemas_votacion,
        name="documentacion_sistemas_votacion",
    ),

    # ===============================
    # LISTAS PREVIAS DE CANDIDATOS
    # ===============================

    # Listado general (lista de listas)
    path(
        "listas/",
        views.lista_candidatos_listado,
        name="lista_candidatos_listado",
    ),

    # Crear nueva lista (crea en BORRADOR y redirige a configurar)
    path(
        "listas/nueva/",
        views.lista_candidatos_nueva,
        name="lista_candidatos_nueva",
    ),

    # Editar / configurar una lista existente
    path(
        "listas/<int:pk>/",
        views.lista_candidatos_configurar,
        name="lista_candidatos_configurar",
    ),

    # Eliminar una lista
    path(
        "listas/<int:pk>/eliminar/",
        views.lista_candidatos_eliminar,
        name="lista_candidatos_eliminar",
    ),
    # ⬇️ ESTA LÍNEA ES LA QUE FALTABA
path("eliminar/<int:pk>/", views.eliminar_votacion, name="eliminar_votacion"),

    # Cambiar estado (aprobar lista)
    path(
        "listas/<int:pk>/estado/",
        views.lista_candidatos_cambiar_estado,
        name="lista_candidatos_cambiar_estado",
    ),
 
    # Reporte de lista de candidatos
path(
    "listas/<int:pk>/reporte/",
    views.reporte_lista_candidatos,
    name="lista_candidatos_reporte"
),
    path(
        "listas/api/buscar-miembro/",
        views.lista_candidatos_buscar_miembro,
        name="lista_candidatos_buscar_miembro",
    ),

    path(
    "listas/<int:pk>/duplicar/",
    views.lista_candidatos_duplicar,
    name="lista_candidatos_duplicar",
),



]
