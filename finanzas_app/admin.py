from django.contrib import admin
from .models import CuentaFinanciera, CategoriaMovimiento, MovimientoFinanciero


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
