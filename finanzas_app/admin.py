from django.contrib import admin
from .models import CuentaFinanciera, CategoriaMovimiento, MovimientoFinanciero, AdjuntoMovimiento

@admin.register(CuentaFinanciera)
class CuentaFinancieraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "moneda", "saldo_inicial", "esta_activa")
    list_filter = ("tipo", "moneda", "esta_activa")
    search_fields = ("nombre",)


@admin.register(CategoriaMovimiento)
class CategoriaMovimientoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "activo", "es_editable")
    list_filter = ("tipo", "activo", "es_editable")
    search_fields = ("nombre",)


@admin.register(MovimientoFinanciero)
class MovimientoFinancieroAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "tipo",
        "cuenta",
        "categoria",
        "monto",
        "creado_por",
    )
    list_filter = ("tipo", "cuenta", "categoria", "fecha")
    search_fields = ("descripcion", "referencia")
    date_hierarchy = "fecha"

@admin.register(AdjuntoMovimiento)
class AdjuntoMovimientoAdmin(admin.ModelAdmin):
    list_display = ("nombre_original", "movimiento", "tamaño_formateado", "subido_por", "subido_en")
    list_filter = ("subido_en", "tipo_mime")
    search_fields = ("nombre_original", "movimiento__descripcion")
    date_hierarchy = "subido_en"
    readonly_fields = ("tamaño", "tipo_mime", "subido_por", "subido_en")