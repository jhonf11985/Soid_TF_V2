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
