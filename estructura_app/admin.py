from django.contrib import admin
from .models import CategoriaUnidad, TipoUnidad, RolUnidad, Unidad, UnidadMembresia, UnidadCargo, MovimientoUnidad


@admin.register(TipoUnidad)
class TipoUnidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "activo")
    list_editable = ("orden", "activo")
    search_fields = ("nombre",)
    ordering = ("orden", "nombre")


@admin.register(RolUnidad)
class RolUnidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "orden", "activo")
    list_editable = ("tipo", "orden", "activo")
    search_fields = ("nombre", "descripcion")
    list_filter = ("tipo", "activo")
    ordering = ("orden", "nombre")



class UnidadMembresiaInline(admin.TabularInline):
    model = UnidadMembresia
    extra = 0
    autocomplete_fields = ("miembo_fk",)
    fields = ("miembo_fk", "tipo", "activo", "fecha_ingreso", "fecha_salida", "notas")
    show_change_link = True


class UnidadCargoInline(admin.TabularInline):
    model = UnidadCargo
    extra = 0
    autocomplete_fields = ("miembo_fk", "rol")
    fields = ("rol", "miembo_fk", "vigente", "fecha_inicio", "fecha_fin", "notas")
    show_change_link = True

class MovimientoUnidadInline(admin.TabularInline):
    model = MovimientoUnidad
    extra = 0
    fields = ("fecha", "tipo", "concepto", "monto", "anulado")
    readonly_fields = ()
    show_change_link = True

@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "padre", "activa", "ruta_admin")
    list_filter = ("tipo", "activa")
    search_fields = ("nombre", "descripcion")
    ordering = ("tipo__orden", "nombre")
    inlines = (UnidadCargoInline, UnidadMembresiaInline, MovimientoUnidadInline)
    autocomplete_fields = ("padre",)
    
    def ruta_admin(self, obj):
        return obj.ruta
    ruta_admin.short_description = "Ruta"


@admin.register(CategoriaUnidad)
class CategoriaUnidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "orden", "activo")
    list_editable = ("orden", "activo")
    search_fields = ("nombre", "codigo")
    ordering = ("orden", "nombre")

@admin.register(MovimientoUnidad)
class MovimientoUnidadAdmin(admin.ModelAdmin):
    list_display = ("unidad", "fecha", "tipo", "concepto", "monto", "anulado")
    list_filter = ("tipo", "anulado", "fecha", "unidad")
    search_fields = ("concepto", "descripcion", "unidad__nombre")
    ordering = ("-fecha", "-id")
