from django.contrib import admin
from django.db.models import Count

from .models import (
    ProgramaEducativo,
    CicloPrograma,
    GrupoFormativo,
    InscripcionGrupo,
    SesionGrupo,
    AsistenciaSesion,
)


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
    search_fields = ("nombre", "programa__nombre")
    list_filter = ("sexo_permitido", "activo", "programa")


@admin.register(InscripcionGrupo)
class InscripcionGrupoAdmin(admin.ModelAdmin):
    list_display = ("miembro_id", "grupo", "estado", "fecha_inscripcion")
    search_fields = ("miembro_id", "grupo__nombre", "grupo__programa__nombre")
    list_filter = ("estado", "grupo__programa")
    list_select_related = ("grupo",)


# =========================
# ✅ ASISTENCIA (KIOSKO)
# =========================

class AsistenciaSesionInline(admin.TabularInline):
    model = AsistenciaSesion
    extra = 0
    can_delete = False

    # ✅ No usamos 'estado' porque tu AsistenciaSesion no lo tiene
    fields = ("miembro", "marcado_en")
    readonly_fields = ("marcado_en",)
    ordering = ("marcado_en",)


@admin.register(SesionGrupo)
class SesionGrupoAdmin(admin.ModelAdmin):
    list_display = ("id", "grupo", "fecha", "estado", "inicio", "fin", "total_presentes")
    list_filter = ("grupo", "fecha", "estado")
    search_fields = ("grupo__nombre",)
    list_select_related = ("grupo",)
    inlines = (AsistenciaSesionInline,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # ✅ AQUÍ ESTÁ LA CORRECCIÓN: el reverse es "asistencias"
        return qs.annotate(_presentes=Count("asistencias", distinct=True))

    @admin.display(description="Presentes")
    def total_presentes(self, obj):
        return getattr(obj, "_presentes", 0)


@admin.register(AsistenciaSesion)
class AsistenciaSesionAdmin(admin.ModelAdmin):
    list_display = ("id", "sesion", "grupo", "miembro", "marcado_en")
    list_filter = ("sesion__fecha", "sesion__grupo")
    search_fields = ("sesion__grupo__nombre", "miembro__nombre", "miembro__apellidos")
    list_select_related = ("sesion", "sesion__grupo", "miembro")
    ordering = ("-marcado_en",)

    @admin.display(description="Grupo")
    def grupo(self, obj):
        return obj.sesion.grupo
