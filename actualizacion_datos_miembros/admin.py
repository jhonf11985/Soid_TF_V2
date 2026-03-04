from django.contrib import admin
from django import forms
from .models import (
    AccesoActualizacionDatos,
    SolicitudActualizacionMiembro,
    SolicitudAltaMiembro,
    AltaMasivaConfig,
    ActualizacionDatosConfig,
    AccesoAltaFamilia,
    AltaFamiliaLog,
)


class TenantAdminMixin:
    """
    Mixin para filtrar por tenant en el admin.
    - Superusers ven todo
    - Usuarios normales solo ven su tenant
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        tenant = getattr(request, 'tenant', None)
        if tenant:
            return qs.filter(tenant=tenant)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not obj.tenant_id:
            tenant = getattr(request, 'tenant', None)
            if tenant:
                obj.tenant = tenant
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'tenant' and not request.user.is_superuser:
            tenant = getattr(request, 'tenant', None)
            if tenant:
                from tenants.models import Tenant
                kwargs['queryset'] = Tenant.objects.filter(pk=tenant.pk)
                kwargs['initial'] = tenant
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AccesoActualizacionDatos)
class AccesoActualizacionDatosAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("miembro", "token", "activo", "ultimo_envio_en", "actualizado_en", "tenant")
    search_fields = ("miembro__nombres", "miembro__apellidos", "miembro__codigo", "token")
    list_filter = ("activo", "tenant")
    raw_id_fields = ("miembro",)


@admin.register(SolicitudActualizacionMiembro)
class SolicitudActualizacionMiembroAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("id", "miembro", "estado", "creado_en", "revisado_en", "revisado_por", "tenant")
    search_fields = ("miembro__nombres", "miembro__apellidos", "miembro__codigo")
    list_filter = ("estado", "tenant")
    raw_id_fields = ("miembro",)


@admin.register(SolicitudAltaMiembro)
class SolicitudAltaMiembroAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("id", "nombres", "apellidos", "telefono", "estado", "creado_en", "tenant")
    list_filter = ("estado", "estado_miembro", "genero", "tenant")
    search_fields = ("nombres", "apellidos", "telefono", "cedula")
    readonly_fields = ("creado_en", "ip_origen", "user_agent", "revisado_en", "revisado_por")

    fieldsets = (
        ("Tenant", {
            "fields": ("tenant",)
        }),
        ("Estado", {
            "fields": ("estado", "nota_admin", "revisado_en", "revisado_por")
        }),
        ("Datos personales", {
            "fields": ("nombres", "apellidos", "genero", "fecha_nacimiento", "estado_miembro")
        }),
        ("Contacto", {
            "fields": ("telefono", "whatsapp")
        }),
        ("Ubicación", {
            "fields": ("sector", "direccion")
        }),
        ("Documentos", {
            "fields": ("cedula", "foto")
        }),
        ("Auditoría", {
            "fields": ("creado_en", "ip_origen", "user_agent")
        }),
    )


@admin.register(AltaMasivaConfig)
class AltaMasivaConfigAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("tenant", "activo", "actualizado_en")
    list_filter = ("activo", "tenant")


@admin.register(ActualizacionDatosConfig)
class ActualizacionDatosConfigAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("tenant", "activo", "actualizado_en")
    list_filter = ("activo", "tenant")


@admin.register(AccesoAltaFamilia)
class AccesoAltaFamiliaAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("token", "activo", "creado_en", "ultimo_envio_en", "tenant")
    list_filter = ("activo", "tenant")
    search_fields = ("token",)


@admin.register(AltaFamiliaLog)
class AltaFamiliaLogAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("id", "principal", "estado", "creado_en", "revisado_en", "tenant")
    list_filter = ("estado", "tenant")
    search_fields = ("principal__nombres", "principal__apellidos")
    raw_id_fields = ("principal", "acceso")
    readonly_fields = ("creado_en", "ip_origen", "user_agent", "revisado_en", "revisado_por")


# Form para configuración (se usa en views, no en admin)
class ActualizacionDatosConfigForm(forms.Form):
    activo = forms.BooleanField(required=False, initial=True, label="Formulario público activo")

    campos_permitidos = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[],
        label="Campos a solicitar (público)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = [
            ("telefono", "Teléfono"),
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),
            ("direccion", "Dirección"),
            ("sector", "Sector"),
            ("ciudad", "Ciudad"),
            ("provincia", "Provincia"),
            ("codigo_postal", "Código postal"),
            ("empleador", "Empleador"),
            ("puesto", "Puesto"),
            ("telefono_trabajo", "Teléfono trabajo"),
            ("direccion_trabajo", "Dirección trabajo"),
            ("contacto_emergencia_nombre", "Contacto emergencia (Nombre)"),
            ("contacto_emergencia_telefono", "Contacto emergencia (Teléfono)"),
            ("contacto_emergencia_relacion", "Contacto emergencia (Relación)"),
            ("tipo_sangre", "Tipo de sangre"),
            ("alergias", "Alergias"),
            ("condiciones_medicas", "Condiciones médicas"),
            ("medicamentos", "Medicamentos"),
        ]
        self.fields["campos_permitidos"].choices = choices