from django.contrib import admin
from .models import EvaluacionUnidad, EvaluacionMiembro


@admin.register(EvaluacionUnidad)
class EvaluacionUnidadAdmin(admin.ModelAdmin):
    list_display = ("unidad", "mes", "anio", "estado", "creado_por", "creado_en")
    list_filter = ("estado", "anio", "mes")
    search_fields = ("unidad__nombre",)


@admin.register(EvaluacionMiembro)
class EvaluacionMiembroAdmin(admin.ModelAdmin):
    list_display = ("miembro", "evaluacion", "asistencia", "participacion", "estado", "puntaje_general", "creado_en")
    list_filter = ("estado", "puntaje_general")
    search_fields = ("miembro__nombres", "miembro__apellidos", "evaluacion__unidad__nombre")
