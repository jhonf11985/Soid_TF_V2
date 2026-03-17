# notificaciones_app/context_processors.py

from django.conf import settings
from .models import Notification


def notificaciones_context(request):
    """
    Añade al contexto global:
    - NOTIF_NO_LEIDAS: últimas notificaciones no leídas (máx. 5)
    - NOTIF_TOTAL_NO_LEIDAS: total de no leídas
    - VAPID_PUBLIC_KEY: clave pública para push notifications
    """
    # VAPID siempre disponible (para la página de perfil)
    vapid_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')
    
    tenant = getattr(request, 'tenant', None)
    
    if not request.user.is_authenticated or not tenant:
        return {
            "VAPID_PUBLIC_KEY": vapid_key,
        }

    qs = Notification.objects.filter(
        tenant=tenant,
        usuario=request.user,
        leida=False
    ).order_by("-fecha_creacion")

    return {
        "NOTIF_NO_LEIDAS": qs[:5],
        "NOTIF_TOTAL_NO_LEIDAS": qs.count(),
        "VAPID_PUBLIC_KEY": vapid_key,
    }