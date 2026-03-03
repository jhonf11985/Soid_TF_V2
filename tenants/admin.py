from django.contrib import admin
from .models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "slug", "dominio", "activo", "creado")
    search_fields = ("nombre", "slug", "dominio")
    list_filter = ("activo",)