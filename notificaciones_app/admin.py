# notificaciones_app/admin.py

from django.contrib import admin
from .models import Notification, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "usuario",
        "tenant",
        "tipo",
        "leida",
        "fecha_creacion",
    )
    list_filter = ("tenant", "tipo", "leida", "fecha_creacion")
    search_fields = (
        "titulo",
        "mensaje",
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
    )
    readonly_fields = ("fecha_creacion",)
    raw_id_fields = ("usuario",)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Superusuarios ven todo
        if request.user.is_superuser:
            return qs
        # Filtrar por tenant si está disponible
        tenant = getattr(request, 'tenant', None)
        if tenant:
            return qs.filter(tenant=tenant)
        return qs


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "tenant", "activo", "creado_en", "actualizado_en")
    list_filter = ("tenant", "activo", "creado_en")
    search_fields = ("user__username", "user__first_name", "endpoint")
    readonly_fields = ("creado_en", "actualizado_en")
    raw_id_fields = ("user",)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Superusuarios ven todo
        if request.user.is_superuser:
            return qs
        # Filtrar por tenant si está disponible
        tenant = getattr(request, 'tenant', None)
        if tenant:
            return qs.filter(tenant=tenant)
        return qs