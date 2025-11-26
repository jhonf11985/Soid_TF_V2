from django.contrib import admin
from .models import Module, ConfiguracionSistema


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "url_name", "is_enabled", "order")
    list_filter = ("is_enabled",)
    search_fields = ("name", "code", "url_name")
    list_editable = ("is_enabled", "order")


@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    """
    Solo permitimos un registro de configuración del sistema.
    """
    list_display = ("nombre_iglesia", "email_oficial", "telefono_oficial")

    # Evitar que se creen más de un registro
    def has_add_permission(self, request):
        from .models import ConfiguracionSistema
        if ConfiguracionSistema.objects.exists():
            return False
        return super().has_add_permission(request)
