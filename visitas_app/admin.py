from django.contrib import admin
from .models import Visita, ClasificacionVisita


@admin.register(ClasificacionVisita)
class ClasificacionVisitaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "orden")
    list_editable = ("activo", "orden")
    search_fields = ("nombre", "descripcion")
    list_filter = ("activo",)
    ordering = ("orden", "nombre")


@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "telefono",
        "clasificacion",
        "genero",
        "edad",
        "fecha_primera_visita",
        "fecha_ultima_visita",
        "cantidad_visitas",
        "estado",
    )
    search_fields = (
        "nombre",
        "telefono",
        "invitado_por",
        "peticion_oracion",
        "notas",
    )
    list_filter = (
        "clasificacion",
        "estado",
        "genero",
        "desea_contacto",
        "primera_vez",
        "fecha_primera_visita",
        "fecha_ultima_visita",
    )
    autocomplete_fields = ("clasificacion",)
    ordering = ("-fecha_ultima_visita", "-id")