from django.contrib import admin
from .models import QrToken, QrScanLog


@admin.register(QrToken)
class QrTokenAdmin(admin.ModelAdmin):
    list_display = ("token", "miembro_id", "activo", "creado_en", "expira_en")
    list_filter = ("activo",)
    search_fields = ("token", "miembro_id")


@admin.register(QrScanLog)
class QrScanLogAdmin(admin.ModelAdmin):
    list_display = ("token", "modo", "resultado", "escaneado_por", "creado_en")
    list_filter = ("modo", "resultado")
    search_fields = ("token__token",)
from .models import QrEnvio


@admin.register(QrEnvio)
class QrEnvioAdmin(admin.ModelAdmin):
    list_display = ("miembro_id", "estado", "telefono", "creado_en", "enviado_en")
    list_filter = ("estado",)
    search_fields = ("miembro_id", "telefono", "token__token")
