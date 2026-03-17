# agenda_app/admin.py

from django.contrib import admin
from .models import Actividad, ActividadRecordatorio


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "hora_inicio",
        "titulo",
        "tenant",
        "tipo",
        "estado",
        "lugar",
        "responsable_texto",
    )
    list_filter = ("tenant", "tipo", "estado", "fecha")
    search_fields = ("titulo", "lugar", "responsable_texto", "descripcion")
    ordering = ("fecha", "hora_inicio", "titulo")
    raw_id_fields = ("unidad",)

    fieldsets = (
        ("Tenant", {
            "fields": ("tenant",)
        }),
        ("Información principal", {
            "fields": ("titulo", "fecha", ("hora_inicio", "hora_fin"), "tipo", "estado", "visibilidad")
        }),
        ("Detalles", {
            "fields": ("unidad", "lugar", "responsable_texto", "descripcion")
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        tenant = getattr(request, 'tenant', None)
        if tenant:
            return qs.filter(tenant=tenant)
        return qs


@admin.register(ActividadRecordatorio)
class ActividadRecordatorioAdmin(admin.ModelAdmin):
    list_display = ("actividad", "get_tenant", "minutos_antes", "enviado_en", "creado_en")
    list_filter = ("minutos_antes", "enviado_en", "actividad__tenant")
    search_fields = ("actividad__titulo",)
    raw_id_fields = ("actividad",)

    @admin.display(description="Tenant")
    def get_tenant(self, obj):
        return obj.actividad.tenant if obj.actividad else "-"

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("actividad__tenant")
        if request.user.is_superuser:
            return qs
        tenant = getattr(request, 'tenant', None)
        if tenant:
            return qs.filter(actividad__tenant=tenant)
        return qs