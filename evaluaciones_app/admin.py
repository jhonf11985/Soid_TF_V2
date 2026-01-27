from django.contrib import admin
from .models import EvaluacionUnidad, EvaluacionMiembro


@admin.register(EvaluacionUnidad)
class EvaluacionUnidadAdmin(admin.ModelAdmin):
    list_display = ("unidad", "mes", "anio", "estado_workflow", "diagnostico", "creado_por", "creado_en")
    list_filter = ("estado_workflow", "diagnostico", "anio", "mes", "unidad")
    search_fields = ("unidad__nombre",)


@admin.register(EvaluacionMiembro)
class EvaluacionMiembroAdmin(admin.ModelAdmin):
    list_display = ("miembro", "evaluacion", "asistencia", "participacion", "puntaje_general", "estado")
    list_filter = ("estado", "puntaje_general")
    search_fields = ("miembro__nombres", "miembro__apellidos")