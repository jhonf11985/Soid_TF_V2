# notificaciones_app/context_processors.py
# notificaciones_app/context_processors.py

from django.conf import settings
from .models import Notification


def notificaciones_context(request):
    """
    Añade al contexto global las notificaciones del usuario autenticado.
    """
    if not request.user.is_authenticated:
        return {
            "VAPID_PUBLIC_KEY": settings.VAPID_PUBLIC_KEY,
        }

    qs = Notification.objects.filter(usuario=request.user, leida=False).order_by("-fecha_creacion")

    return {
        "NOTIF_NO_LEIDAS": qs[:5],
        "NOTIF_TOTAL_NO_LEIDAS": qs.count(),
        "VAPID_PUBLIC_KEY": settings.VAPID_PUBLIC_KEY,
    }