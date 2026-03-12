from django.contrib import admin
from .models import (
    TipoRegistroVisita,
    ClasificacionVisita,
    RegistroVisitas,
    Visita,
)


@admin.register(TipoRegistroVisita)
class TipoRegistroVisitaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "orden")
    list_editable = ("activo", "orden")
    search_fields = ("nombre", "descripcion")
    list_filter = ("activo",)
    ordering = ("orden", "nombre")


@admin.register(ClasificacionVisita)
class ClasificacionVisitaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "orden")
    list_editable = ("activo", "orden")
    search_fields = ("nombre", "descripcion")
    list_filter = ("activo",)
    ordering = ("orden", "nombre")


class VisitaInline(admin.TabularInline):
    model = Visita
    extra = 1
    fields = (
        "nombre",
        "telefono",
        "genero",
        "edad",
        "clasificacion",
        "primera_vez",
        "invitado_por",
        "desea_contacto",
        "estado",
    )


@admin.register(RegistroVisitas)
class RegistroVisitasAdmin(admin.ModelAdmin):
    list_display = ("fecha", "tipo", "unidad_responsable", "total_visitas")
    list_filter = ("fecha", "tipo", "unidad_responsable")
    search_fields = ("tipo__nombre", "unidad_responsable__nombre", "observaciones")
    autocomplete_fields = ("tipo", "unidad_responsable")
    inlines = [VisitaInline]
    ordering = ("-fecha", "-id")

    def total_visitas(self, obj):
        return obj.visitas.count()

    total_visitas.short_description = "Total visitas"


@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "telefono",
        "registro",
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
        "registro__tipo__nombre",
        "registro__unidad_responsable__nombre",
    )
    list_filter = (
        "clasificacion",
        "estado",
        "genero",
        "desea_contacto",
        "primera_vez",
        "fecha_primera_visita",
        "fecha_ultima_visita",
        "registro__tipo",
        "registro__unidad_responsable",
    )
    autocomplete_fields = ("clasificacion", "registro")
    ordering = ("-fecha_ultima_visita", "-id")