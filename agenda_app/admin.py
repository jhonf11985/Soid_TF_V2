from django.contrib import admin
from .models import Actividad


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "hora_inicio",
        "titulo",
        "tipo",
        "estado",
        "lugar",
        "responsable_texto",
    )
    list_filter = ("tipo", "estado", "fecha")
    search_fields = ("titulo", "lugar", "responsable_texto", "descripcion")
    ordering = ("fecha", "hora_inicio", "titulo")

    fieldsets = (
        ("Información principal", {
            "fields": ("titulo", "fecha", ("hora_inicio", "hora_fin"), "tipo", "estado")
        }),
        ("Detalles", {
            "fields": ("lugar", "responsable_texto", "descripcion")
        }),
    )
