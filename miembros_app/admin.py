from django.contrib import admin
from .models import Miembro


@admin.register(Miembro)
class MiembroAdmin(admin.ModelAdmin):
    list_display = (
        "nombres",
        "apellidos",
        "telefono",
        "email",
        "estado_miembro",
        "fecha_ingreso_iglesia",
    )
    list_filter = (
        "estado_miembro",
        "genero",
        "estado_civil",
        "nivel_educativo",
    )
    search_fields = (
        "nombres",
        "apellidos",
        "telefono",
        "email",
        "iglesia_anterior",
    )
    ordering = ("nombres", "apellidos")
    list_per_page = 25
from .models import MiembroRelacion

@admin.register(MiembroRelacion)
class MiembroRelacionAdmin(admin.ModelAdmin):
    list_display = ("miembro", "familiar", "tipo_relacion", "vive_junto", "es_responsable")
    search_fields = (
        "miembro__nombres",
        "miembro__apellidos",
        "familiar__nombres",
        "familiar__apellidos",
    )
    list_filter = ("tipo_relacion", "vive_junto", "es_responsable")
