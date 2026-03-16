from django.contrib import admin
from .models import CategoriaUnidad, TipoUnidad, RolUnidad, Unidad, UnidadMembresia, UnidadCargo, MovimientoUnidad


class TenantAdminMixin:
    """Mixin para filtrar por tenant en el admin."""
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant') and request.tenant:
            return qs.filter(tenant=request.tenant)
        return qs

    def save_model(self, request, obj, form, change):
        if not change and hasattr(request, 'tenant') and request.tenant:
            obj.tenant = request.tenant
        super().save_model(request, obj, form, change)


@admin.register(TipoUnidad)
class TipoUnidadAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "orden", "activo")
    list_editable = ("orden", "activo")
    search_fields = ("nombre",)
    ordering = ("orden", "nombre")


@admin.register(RolUnidad)
class RolUnidadAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "tipo", "orden", "activo")
    list_editable = ("tipo", "orden", "activo")
    search_fields = ("nombre", "descripcion")
    list_filter = ("tipo", "activo")
    ordering = ("orden", "nombre")


class UnidadMembresiaInline(admin.TabularInline):
    model = UnidadMembresia
    extra = 0
    autocomplete_fields = ("miembo_fk",)
    fields = ("miembo_fk", "tipo", "activo", "fecha_ingreso", "fecha_salida", "notas")
    show_change_link = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant') and request.tenant:
            return qs.filter(tenant=request.tenant)
        return qs


class UnidadCargoInline(admin.TabularInline):
    model = UnidadCargo
    extra = 0
    autocomplete_fields = ("miembo_fk", "rol")
    fields = ("rol", "miembo_fk", "vigente", "fecha_inicio", "fecha_fin", "notas")
    show_change_link = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant') and request.tenant:
            return qs.filter(tenant=request.tenant)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "rol" and hasattr(request, 'tenant') and request.tenant:
            kwargs["queryset"] = RolUnidad.objects.filter(tenant=request.tenant, activo=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class MovimientoUnidadInline(admin.TabularInline):
    model = MovimientoUnidad
    extra = 0
    fields = ("fecha", "tipo", "concepto", "monto", "anulado")
    readonly_fields = ()
    show_change_link = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant') and request.tenant:
            return qs.filter(tenant=request.tenant)
        return qs


@admin.register(Unidad)
class UnidadAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "tipo", "padre", "activa", "ruta_admin")
    list_filter = ("tipo", "activa")
    search_fields = ("nombre", "descripcion")
    ordering = ("tipo__orden", "nombre")
    inlines = (UnidadCargoInline, UnidadMembresiaInline, MovimientoUnidadInline)
    autocomplete_fields = ("padre",)

    def ruta_admin(self, obj):
        return obj.ruta
    ruta_admin.short_description = "Ruta"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if tenant:
            if db_field.name == "tipo":
                kwargs["queryset"] = TipoUnidad.objects.filter(tenant=tenant, activo=True)
            elif db_field.name == "categoria":
                kwargs["queryset"] = CategoriaUnidad.objects.filter(tenant=tenant, activo=True)
            elif db_field.name == "padre":
                kwargs["queryset"] = Unidad.objects.filter(tenant=tenant, activa=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(CategoriaUnidad)
class CategoriaUnidadAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "codigo", "orden", "activo")
    list_editable = ("orden", "activo")
    search_fields = ("nombre", "codigo")
    ordering = ("orden", "nombre")


@admin.register(MovimientoUnidad)
class MovimientoUnidadAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("unidad", "fecha", "tipo", "concepto", "monto", "anulado")
    list_filter = ("tipo", "anulado", "fecha", "unidad")
    search_fields = ("concepto", "descripcion", "unidad__nombre")
    ordering = ("-fecha", "-id")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "unidad" and hasattr(request, 'tenant') and request.tenant:
            kwargs["queryset"] = Unidad.objects.filter(tenant=request.tenant, activa=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)