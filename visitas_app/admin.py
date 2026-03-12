from django.contrib import admin
from .models import Visita


@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "telefono",
        "tipo",
        "fecha_primera_visita",
        "fecha_ultima_visita",
        "cantidad_visitas",
        "primera_vez",
        "estado",
    )
    list_filter = (
        "tipo",
        "primera_vez",
        "estado",
        "fecha_primera_visita",
        "fecha_ultima_visita",
    )
    search_fields = (
        "nombre",
        "telefono",
        "invitado_por",
    )
    ordering = ("-fecha_ultima_visita", "-id")