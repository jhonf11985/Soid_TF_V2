# notificaciones_app/context_processors.py

from .models import Notification


def notificaciones_context(request):
    """
    Añade al contexto global las notificaciones del usuario autenticado.
    - NOTIF_NO_LEIDAS: últimas notificaciones no leídas (máx. 5)
    - NOTIF_TOTAL_NO_LEIDAS: total de no leídas
    """
    if not request.user.is_authenticated:
        return {}

    qs = Notification.objects.filter(usuario=request.user, leida=False).order_by("-fecha_creacion")

    return {
        "NOTIF_NO_LEIDAS": qs[:5],
        "NOTIF_TOTAL_NO_LEIDAS": qs.count(),
    }
