from django.contrib import admin
from .models import EvaluacionPerfilUnidad, EvaluacionUnidad, EvaluacionMiembro


@admin.register(EvaluacionPerfilUnidad)
class EvaluacionPerfilUnidadAdmin(admin.ModelAdmin):
    list_display = (
        "unidad",
        "modo",
        "frecuencia",
        "usar_pesos",
        "w_asistencia",
        "w_participacion",
        "w_compromiso",
        "w_actitud",
        "w_integracion",
        "w_liderazgo",
        "w_madurez_espiritual",
        "excluir_evaluador",
        "actualizado_en",
    )
    list_filter = ("modo", "frecuencia", "usar_pesos", "excluir_evaluador", "unidad")
    search_fields = ("unidad__nombre",)
    
    fieldsets = (
        ("Unidad", {
            "fields": ("unidad",)
        }),
        ("Modo de evaluación", {
            "fields": ("modo", "frecuencia", "dia_cierre"),
            "description": "En modo LIBRE, la frecuencia y día de cierre no aplican."
        }),
        ("Reglas", {
            "fields": ("permitir_editar_cerrada", "excluir_evaluador", "usar_pesos")
        }),
        ("Dimensiones activas", {
            "fields": (
                "usar_asistencia",
                "usar_participacion",
                "usar_compromiso",
                "usar_actitud",
                "usar_integracion",
                "usar_liderazgo",
                "usar_madurez_espiritual",
                "usar_estado_espiritual",
            )
        }),
        ("Pesos (solo si usar_pesos está activo)", {
            "fields": (
                "w_asistencia",
                "w_participacion",
                "w_compromiso",
                "w_actitud",
                "w_integracion",
                "w_liderazgo",
                "w_madurez_espiritual",
            ),
            "classes": ("collapse",)
        }),
    )


@admin.register(EvaluacionUnidad)
class EvaluacionUnidadAdmin(admin.ModelAdmin):
    list_display = (
        "unidad",
        "mes",
        "anio",
        "estado_workflow",
        "diagnostico",
        "creado_por",
        "creado_en",
    )
    list_filter = ("estado_workflow", "diagnostico", "anio", "mes", "unidad")
    search_fields = ("unidad__nombre",)


@admin.register(EvaluacionMiembro)
class EvaluacionMiembroAdmin(admin.ModelAdmin):
    list_display = (
        "miembro",
        "evaluacion",
        "asistencia",
        "participacion",
        "compromiso",
        "actitud",
        "integracion",
        "liderazgo",
        "madurez_espiritual",
        "estado_espiritual",
        "puntaje_general",
        "evaluado_por",
        "creado_en",
    )
    list_filter = ("estado_espiritual", "puntaje_general", "evaluacion")
    search_fields = ("miembro__nombres", "miembro__apellidos")