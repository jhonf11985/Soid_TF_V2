from django.contrib import admin
from .models import Module


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "url_name", "is_enabled", "order")
    list_filter = ("is_enabled",)
    search_fields = ("name", "code", "url_name")
    list_editable = ("is_enabled", "order")
