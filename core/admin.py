from django.contrib import admin
from django.utils.html import format_html
from .models import Module, ConfiguracionSistema, DocumentoCompartido, UsuarioTemporal


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "url_name", "is_enabled", "order")
    list_filter = ("is_enabled",)
    search_fields = ("name", "code", "url_name")
    list_editable = ("is_enabled", "order")


@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    """
    Configuración por tenant.
    En el admin de Django no se filtra por tenant automáticamente,
    pero el constraint único por tenant evita duplicados.
    """
    list_display = ("tenant", "nombre_iglesia", "email_oficial", "telefono_oficial")
    list_filter = ("tenant",)
    search_fields = ("nombre_iglesia", "email_oficial")

    # ✅ YA NO LIMITAMOS A 1 REGISTRO (ahora es 1 por tenant)
    def has_add_permission(self, request):
        return True


@admin.register(DocumentoCompartido)
class DocumentoCompartidoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tenant", "token", "activo", "creado_en", "expira_en", "creado_por")
    list_filter = ("tenant", "activo")
    search_fields = ("titulo", "token")


@admin.register(UsuarioTemporal)
class UsuarioTemporalAdmin(admin.ModelAdmin):
    list_display = [
        'usuario_display', 
        'tenant',
        'motivo', 
        'estado_display', 
        'dias_restantes_display',
        'accesos_count',
        'fecha_creacion',
        'creado_por'
    ]
    list_filter = ['tenant', 'activo', 'motivo', 'fecha_creacion']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'motivo', 'notas']
    readonly_fields = ['fecha_creacion', 'ultimo_acceso', 'accesos_count', 'password_temporal']
    raw_id_fields = ['user', 'creado_por']
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        ('Tenant', {
            'fields': ('tenant',)
        }),
        ('Usuario', {
            'fields': ('user', 'password_temporal')
        }),
        ('Configuración de Acceso', {
            'fields': ('fecha_expiracion', 'motivo', 'notas', 'activo')
        }),
        ('Información', {
            'fields': ('creado_por', 'fecha_creacion', 'ultimo_acceso', 'accesos_count'),
            'classes': ('collapse',)
        }),
    )
    
    def usuario_display(self, obj):
        nombre = obj.user.get_full_name() or obj.user.username
        return format_html(
            '<strong>{}</strong><br><small style="color:#666;">{}</small>',
            obj.user.username,
            nombre if nombre != obj.user.username else ''
        )
    usuario_display.short_description = 'Usuario'
    
    def estado_display(self, obj):
        if obj.esta_activo:
            return format_html('<span style="color: #16a34a;">● Activo</span>')
        elif obj.esta_expirado:
            return format_html('<span style="color: #dc2626;">● Expirado</span>')
        else:
            return format_html('<span style="color: #6b7280;">● Inactivo</span>')
    estado_display.short_description = 'Estado'
    
    def dias_restantes_display(self, obj):
        if obj.esta_expirado:
            return format_html('<span style="color: #dc2626;">Expirado</span>')
        dias = obj.dias_restantes
        if dias <= 3:
            color = '#d97706'
        else:
            color = '#16a34a'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.tiempo_restante_display
        )
    dias_restantes_display.short_description = 'Tiempo restante'
    
    actions = ['desactivar_seleccionados', 'extender_7_dias', 'extender_15_dias']
    
    @admin.action(description='Desactivar usuarios seleccionados')
    def desactivar_seleccionados(self, request, queryset):
        count = 0
        for ut in queryset:
            ut.desactivar()
            count += 1
        self.message_user(request, f'{count} usuario(s) temporal(es) desactivado(s).')
    
    @admin.action(description='Extender 7 días')
    def extender_7_dias(self, request, queryset):
        count = 0
        for ut in queryset:
            ut.extender(7)
            count += 1
        self.message_user(request, f'{count} usuario(s) extendido(s) 7 días.')
    
    @admin.action(description='Extender 15 días')
    def extender_15_dias(self, request, queryset):
        count = 0
        for ut in queryset:
            ut.extender(15)
            count += 1
        self.message_user(request, f'{count} usuario(s) extendido(s) 15 días.')