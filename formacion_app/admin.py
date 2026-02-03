from django.contrib import admin
from .models import ProgramaEducativo, CicloPrograma, GrupoFormativo, InscripcionGrupo


@admin.register(ProgramaEducativo)
class ProgramaEducativoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "activo", "creado_en")
    search_fields = ("nombre",)
    list_filter = ("tipo", "activo")


@admin.register(CicloPrograma)
class CicloProgramaAdmin(admin.ModelAdmin):
    list_display = ("programa", "nombre", "activo", "fecha_inicio", "fecha_fin")
    search_fields = ("nombre", "programa__nombre")
    list_filter = ("activo", "programa")


@admin.register(GrupoFormativo)
class GrupoFormativoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "programa",
        "sexo_permitido",
        "edad_min",
        "edad_max",
        "maestro",
        "activo",
    )
    search_fields = (
        "nombre",
        "programa__nombre",
    )
    list_filter = (
        "sexo_permitido",
        "activo",
        "programa",
    )
@admin.register(InscripcionGrupo)
class InscripcionGrupoAdmin(admin.ModelAdmin):
    list_display = (
        "miembro_id",
        "grupo",
        "estado",
        "fecha_inscripcion",
    )
    search_fields = (
        "miembro_id",
        "grupo__nombre",
        "grupo__programa__nombre",
    )
    list_filter = (
        "estado",
        "grupo__programa",
    )
