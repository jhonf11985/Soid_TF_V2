from django.contrib import admin
from .models import NuevoCreyenteExpediente


@admin.register(NuevoCreyenteExpediente)
class NuevoCreyenteExpedienteAdmin(admin.ModelAdmin):
    list_display = ("miembro", "estado", "responsable", "fecha_envio", "proximo_contacto", "fecha_cierre")
    list_filter = ("estado", "responsable")
    search_fields = (
        "miembro__nombres",
        "miembro__apellidos",
        "miembro__telefono",
        "miembro__email",
        "miembro__codigo",
    )
    ordering = ("-fecha_envio",)
