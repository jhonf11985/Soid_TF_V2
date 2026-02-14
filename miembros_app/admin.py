# -*- coding: utf-8 -*-
"""
miembros_app/admin.py
Admin completo para el módulo de miembros.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    Miembro, 
    MiembroRelacion, 
    RazonSalidaMiembro,
    ZonaGeo,
    ClanFamiliar,
    HogarFamiliar,
    HogarMiembro,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ZONA GEO
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(ZonaGeo)
class ZonaGeoAdmin(admin.ModelAdmin):
    list_display = ("provincia", "ciudad", "sector", "lat", "lng", "actualizado")
    search_fields = ("provincia", "ciudad", "sector")
    list_filter = ("provincia", "ciudad")
    ordering = ("provincia", "ciudad", "sector")


# ═══════════════════════════════════════════════════════════════════════════════
# RAZONES DE SALIDA
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# MIEMBRO
# ═══════════════════════════════════════════════════════════════════════════════

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

    def save_model(self, request, obj, form, change):
        if obj.razon_salida_id:
            if not obj.fecha_salida:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    "Si defines una razón de salida, debes indicar la fecha de salida."
                )
            if obj.razon_salida.estado_resultante:
                obj.estado_miembro = obj.razon_salida.estado_resultante
            obj.activo = False
        else:
            if obj.fecha_salida:
                obj.fecha_salida = None

        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.razon_salida_id:
            readonly.extend(["estado_miembro", "activo"])
        return readonly


# ═══════════════════════════════════════════════════════════════════════════════
# RELACIONES FAMILIARES (MiembroRelacion)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(MiembroRelacion)
class MiembroRelacionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "miembro_link",
        "tipo_relacion_badge",
        "familiar_link",
        "vive_junto",
        "es_responsable",
    )
    list_filter = ("tipo_relacion", "vive_junto", "es_responsable")
    search_fields = (
        "miembro__nombres",
        "miembro__apellidos",
        "familiar__nombres",
        "familiar__apellidos",
    )
    ordering = ("miembro__nombres", "miembro__apellidos")
    list_per_page = 50
    
    autocomplete_fields = ["miembro", "familiar"]
    
    actions = ["eliminar_seleccionados"]

    @admin.display(description="Miembro")
    def miembro_link(self, obj):
        return format_html(
            '<a href="/admin/miembros_app/miembro/{}/change/">{}</a>',
            obj.miembro.id,
            f"{obj.miembro.nombres} {obj.miembro.apellidos}"
        )

    @admin.display(description="Familiar")
    def familiar_link(self, obj):
        return format_html(
            '<a href="/admin/miembros_app/miembro/{}/change/">{}</a>',
            obj.familiar.id,
            f"{obj.familiar.nombres} {obj.familiar.apellidos}"
        )

    @admin.display(description="Tipo")
    def tipo_relacion_badge(self, obj):
        colores = {
            "conyuge": "#e91e63",
            "padre": "#2196f3",
            "madre": "#9c27b0",
            "hijo": "#4caf50",
            "hermano": "#ff9800",
        }
        color = colores.get(obj.tipo_relacion, "#757575")
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 8px; '
            'border-radius:4px; font-size:11px; font-weight:bold;">{}</span>',
            color,
            obj.get_tipo_relacion_display()
        )

    @admin.action(description="Eliminar relaciones seleccionadas")
    def eliminar_seleccionados(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Se eliminaron {count} relaciones.")


# ═══════════════════════════════════════════════════════════════════════════════
# CLAN FAMILIAR
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(ClanFamiliar)
class ClanFamiliarAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "hogares_count", "creado_en")
    search_fields = ("nombre",)
    ordering = ("nombre",)
    list_per_page = 50
    
    actions = ["eliminar_seleccionados"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(hogares_count=Count("hogares"))

    @admin.display(description="Hogares", ordering="hogares_count")
    def hogares_count(self, obj):
        return obj.hogares_count

    @admin.action(description="Eliminar clanes seleccionados")
    def eliminar_seleccionados(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Se eliminaron {count} clanes.")


# ═══════════════════════════════════════════════════════════════════════════════
# HOGAR FAMILIAR
# ═══════════════════════════════════════════════════════════════════════════════

class HogarMiembroInline(admin.TabularInline):
    model = HogarMiembro
    extra = 0
    autocomplete_fields = ["miembro"]
    fields = ("miembro", "rol", "es_principal")


@admin.register(HogarFamiliar)
class HogarFamiliarAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "clan_link", "miembros_count", "miembros_lista", "creado_en")
    list_filter = ("clan",)
    search_fields = ("nombre", "clan__nombre")
    ordering = ("nombre",)
    list_per_page = 50
    
    inlines = [HogarMiembroInline]
    autocomplete_fields = ["clan"]
    
    actions = ["eliminar_seleccionados"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("miembros__miembro").annotate(
            miembros_count=Count("miembros")
        )

    @admin.display(description="Clan")
    def clan_link(self, obj):
        if obj.clan:
            return format_html(
                '<a href="/admin/miembros_app/clanfamiliar/{}/change/">{}</a>',
                obj.clan.id,
                obj.clan.nombre
            )
        return "—"

    @admin.display(description="# Miembros", ordering="miembros_count")
    def miembros_count(self, obj):
        count = obj.miembros_count
        color = "#4caf50" if count > 0 else "#999"
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 8px; '
            'border-radius:10px; font-size:11px;">{}</span>',
            color, count
        )

    @admin.display(description="Miembros")
    def miembros_lista(self, obj):
        miembros = obj.miembros.all()[:5]
        nombres = [f"{hm.miembro.nombres} ({hm.get_rol_display()})" for hm in miembros]
        if obj.miembros.count() > 5:
            nombres.append("...")
        return ", ".join(nombres) if nombres else "—"

    @admin.action(description="Eliminar hogares seleccionados")
    def eliminar_seleccionados(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Se eliminaron {count} hogares.")


# ═══════════════════════════════════════════════════════════════════════════════
# HOGAR MIEMBRO (registro intermedio)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(HogarMiembro)
class HogarMiembroAdmin(admin.ModelAdmin):
    list_display = ("id", "miembro_link", "hogar_link", "rol_badge", "es_principal_icon")
    list_filter = ("rol", "es_principal", "hogar")
    search_fields = (
        "miembro__nombres",
        "miembro__apellidos",
        "hogar__nombre",
    )
    ordering = ("hogar__nombre", "miembro__nombres")
    list_per_page = 50
    
    autocomplete_fields = ["hogar", "miembro"]
    
    actions = ["eliminar_seleccionados", "marcar_como_principal", "quitar_principal"]

    @admin.display(description="Miembro")
    def miembro_link(self, obj):
        return format_html(
            '<a href="/admin/miembros_app/miembro/{}/change/">{} {}</a>',
            obj.miembro.id,
            obj.miembro.nombres,
            obj.miembro.apellidos
        )

    @admin.display(description="Hogar")
    def hogar_link(self, obj):
        return format_html(
            '<a href="/admin/miembros_app/hogarfamiliar/{}/change/">{}</a>',
            obj.hogar.id,
            obj.hogar.nombre or f"Hogar #{obj.hogar.id}"
        )

    @admin.display(description="Rol")
    def rol_badge(self, obj):
        colores = {
            "padre": "#2196f3",
            "madre": "#e91e63",
            "hijo": "#4caf50",
            "abuelo": "#ff9800",
            "otro": "#757575",
        }
        color = colores.get(obj.rol, "#757575")
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 8px; '
            'border-radius:4px; font-size:11px;">{}</span>',
            color,
            obj.get_rol_display()
        )

    @admin.display(description="Principal", boolean=True)
    def es_principal_icon(self, obj):
        return obj.es_principal

    @admin.action(description="Marcar como principal")
    def marcar_como_principal(self, request, queryset):
        queryset.update(es_principal=True)
        self.message_user(request, f"Se marcaron {queryset.count()} como principales.")

    @admin.action(description="Quitar marca de principal")
    def quitar_principal(self, request, queryset):
        queryset.update(es_principal=False)
        self.message_user(request, f"Se quitó la marca de principal a {queryset.count()}.")

    @admin.action(description="Eliminar seleccionados")
    def eliminar_seleccionados(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Se eliminaron {count} registros.")