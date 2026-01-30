# notificaciones_app/admin.py

from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "usuario",
        "tipo",
        "leida",
        "fecha_creacion",
    )
    list_filter = ("tipo", "leida", "fecha_creacion")
    search_fields = ("titulo", "mensaje", "usuario__username", "usuario__first_name", "usuario__last_name")
    readonly_fields = ("fecha_creacion",)

from .models import PushSubscription

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'activo', 'creado_en', 'actualizado_en']
    list_filter = ['activo']