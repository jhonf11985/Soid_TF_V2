from django.contrib import admin
from .models import AccesoActualizacionDatos, SolicitudActualizacionMiembro


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
