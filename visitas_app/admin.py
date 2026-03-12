from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Visita


@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "telefono",
        "tipo",
        "fecha_visita",
        "primera_vez",
        "estado",
    )
    list_filter = ("tipo", "primera_vez", "estado", "fecha_visita")
    search_fields = ("nombre", "telefono", "invitado_por")
    ordering = ("-fecha_visita", "-id")