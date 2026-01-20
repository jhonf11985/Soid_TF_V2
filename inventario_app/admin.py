
from django.contrib import admin
from .models import CategoriaRecurso, Ubicacion, Recurso, MovimientoRecurso


@admin.register(CategoriaRecurso)
class CategoriaRecursoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "categoria", "ubicacion", "cantidad_total", "estado", "actualizado_en")
    list_filter = ("estado", "categoria", "ubicacion")
    search_fields = ("codigo", "nombre")
    ordering = ("nombre", "codigo")
    autocomplete_fields = ("categoria", "ubicacion")


@admin.register(MovimientoRecurso)
class MovimientoRecursoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "tipo", "recurso", "cantidad", "ubicacion_origen", "ubicacion_destino")
    list_filter = ("tipo", "fecha")
    search_fields = ("recurso__codigo", "recurso__nombre", "motivo")
    autocomplete_fields = ("recurso", "ubicacion_origen", "ubicacion_destino")
    ordering = ("-fecha",)

