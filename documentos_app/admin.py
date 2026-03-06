from django.contrib import admin

from .models import Carpeta, CategoriaDocumento, Documento, EtiquetaDocumento


@admin.register(Carpeta)
class CarpetaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "tenant",
        "carpeta_padre",
        "visibilidad",
        "propietario",
        "activa",
        "created_at",
    )
    list_filter = ("tenant", "visibilidad", "activa", "created_at")
    search_fields = ("nombre", "descripcion", "slug")
    prepopulated_fields = {}
    ordering = ("tenant", "orden", "nombre")


@admin.register(CategoriaDocumento)
class CategoriaDocumentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tenant", "color", "icono", "activa", "orden")
    list_filter = ("tenant", "activa")
    search_fields = ("nombre", "descripcion", "slug")
    ordering = ("tenant", "orden", "nombre")


@admin.register(EtiquetaDocumento)
class EtiquetaDocumentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tenant", "color", "activa", "created_at")
    list_filter = ("tenant", "activa", "created_at")
    search_fields = ("nombre", "slug")
    ordering = ("tenant", "nombre")


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "tenant",
        "carpeta",
        "categoria",
        "estado",
        "visibilidad",
        "es_oficial",
        "activo",
        "eliminado",
        "created_at",
    )
    list_filter = (
        "tenant",
        "estado",
        "visibilidad",
        "es_oficial",
        "activo",
        "eliminado",
        "categoria",
        "created_at",
    )
    search_fields = ("titulo", "descripcion", "archivo")
    filter_horizontal = ("etiquetas",)
    ordering = ("-created_at", "titulo")