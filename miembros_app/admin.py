from django.contrib import admin
from .models import Miembro, MiembroRelacion, RazonSalidaMiembro
from django.core.exceptions import ValidationError


from .models import ZonaGeo

@admin.register(ZonaGeo)
class ZonaGeoAdmin(admin.ModelAdmin):
    list_display = ("provincia", "ciudad", "sector", "lat", "lng", "actualizado")
    search_fields = ("provincia", "ciudad", "sector")
    list_filter = ("provincia", "ciudad")

# ---------------------------
#  ADMIN PARA RAZONES DE SALIDA
# ---------------------------
@admin.register(RazonSalidaMiembro)
class RazonSalidaMiembroAdmin(admin.ModelAdmin):
    list_display = ("nombre", "aplica_a", "estado_resultante", "permite_carta", "activo", "orden")
    list_filter = ("activo", "aplica_a", "estado_resultante", "permite_carta")
    search_fields = ("nombre", "descripcion")
    ordering = ("orden", "nombre")

    list_editable = ("aplica_a", "estado_resultante", "permite_carta", "activo", "orden")

    fieldsets = (
        ("Datos principales", {
            "fields": ("nombre", "descripcion", "activo", "orden")
        }),
        ("Reglas del sistema", {
            "fields": ("aplica_a", "estado_resultante", "permite_carta"),
            "description": "Estas reglas controlan el estado pastoral automático y si aplica carta."
        }),
    )


# ---------------------------
#  ADMIN PARA MIEMBRO
# ---------------------------
@admin.register(Miembro)
class MiembroAdmin(admin.ModelAdmin):
    list_display = (
        "nombres",
        "apellidos",
        "telefono",
        "email",
        "estado_miembro",
        "activo",
        "fecha_ingreso_iglesia",
    )

    list_filter = (
        "estado_miembro",
        "activo",
        "genero",
        "estado_civil",
        "nivel_educativo",
       "rol_ministerial",
        "tiene_credenciales",
        "obrero_ordenado",
        "bautizado_espiritu_santo",
        "misionero_activo",

    )

    search_fields = (
        "nombres",
        "apellidos",
        "telefono",
        "email",
        "iglesia_anterior",
                "donde_estudio_teologia",
        "preparacion_teologica",
        "mision_pais",
        "mision_ciudad",

    )

    ordering = ("nombres", "apellidos")
    list_per_page = 25

    # 🔒 REGLAS DE NEGOCIO EN ADMIN
    def save_model(self, request, obj, form, change):
        if obj.razon_salida_id:
            # Fecha de salida obligatoria
            if not obj.fecha_salida:
                raise ValidationError(
                    "Si defines una razón de salida, debes indicar la fecha de salida."
                )

            # Estado automático según razón
            if obj.razon_salida.estado_resultante:
                obj.estado_miembro = obj.razon_salida.estado_resultante

            # Activo SIEMPRE falso si hay salida
            obj.activo = False

        else:
            # Si no hay razón de salida, no debe existir fecha
            if obj.fecha_salida:
                obj.fecha_salida = None

        super().save_model(request, obj, form, change)

    # 🔒 Bloquear edición manual cuando hay salida
    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.razon_salida_id:
            readonly.extend(["estado_miembro", "activo"])
        return readonly


# ---------------------------
#  ADMIN PARA RELACIONES
# ---------------------------
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
    ordering = ("miembro__nombres", "miembro__apellidos")