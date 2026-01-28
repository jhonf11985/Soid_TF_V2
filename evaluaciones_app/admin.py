from django.contrib import admin
from .models import EvaluacionPerfilUnidad, EvaluacionUnidad, EvaluacionMiembro


@admin.register(EvaluacionPerfilUnidad)
class EvaluacionPerfilUnidadAdmin(admin.ModelAdmin):
    list_display = (
        "unidad",
        "modo",
        "w_asistencia",
        "w_participacion",
        "w_compromiso",
        "w_actitud",
        "w_integracion",
        "w_madurez_espiritual",
        "excluir_evaluador",
        "actualizado_en",
    )
    list_filter = ("modo", "excluir_evaluador", "unidad")
    search_fields = ("unidad__nombre",)


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
        "madurez_espiritual",
        "estado_espiritual",
        "puntaje_general",
        "evaluado_por",
        "creado_en",
    )
    list_filter = ("estado_espiritual", "puntaje_general", "evaluacion")
    search_fields = ("miembro__nombres", "miembro__apellidos")
