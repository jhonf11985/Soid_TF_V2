from django.contrib import admin
from .models import (
    AccesoActualizacionDatos,
    SolicitudActualizacionMiembro,
    SolicitudAltaMiembro,
    AltaMasivaConfig,
)


@admin.register(AccesoActualizacionDatos)
class AccesoActualizacionDatosAdmin(admin.ModelAdmin):
    list_display = ("miembro", "token", "activo", "ultimo_envio_en", "actualizado_en")
    search_fields = ("miembro__nombres", "miembro__apellidos", "miembro__codigo", "token")
    list_filter = ("activo",)


@admin.register(SolicitudActualizacionMiembro)
class SolicitudActualizacionMiembroAdmin(admin.ModelAdmin):
    list_display = ("id", "miembro", "estado", "creado_en", "revisado_en", "revisado_por")
    search_fields = ("miembro__nombres", "miembro__apellidos", "miembro__codigo")
    list_filter = ("estado",)


@admin.register(SolicitudAltaMiembro)
class SolicitudAltaMiembroAdmin(admin.ModelAdmin):
    list_display = ("id", "nombres", "apellidos", "telefono", "estado", "creado_en")
    list_filter = ("estado", "estado_miembro", "genero")
    search_fields = ("nombres", "apellidos", "telefono", "cedula")
    readonly_fields = ("creado_en", "ip_origen", "user_agent", "revisado_en", "revisado_por")

    fieldsets = (
        ("Estado", {
            "fields": ("estado", "nota_admin", "revisado_en", "revisado_por")
        }),
        ("Datos personales", {
            "fields": ("nombres", "apellidos", "genero", "fecha_nacimiento", "estado_miembro")
        }),
        ("Contacto", {
            "fields": ("telefono", "whatsapp")
        }),
        ("Ubicación", {
            "fields": ("sector", "direccion")
        }),
        ("Documentos", {
            "fields": ("cedula", "foto")
        }),
        ("Auditoría", {
            "fields": ("creado_en", "ip_origen", "user_agent")
        }),
    )


@admin.register(AltaMasivaConfig)
class AltaMasivaConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "activo", "actualizado_en")
