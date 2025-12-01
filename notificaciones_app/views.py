
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def marcar_todas_leidas(request):
    """
    Marca todas las notificaciones no leídas del usuario como leídas.
    """
    Notification.objects.filter(usuario=request.user, leida=False).update(leida=True)
    return JsonResponse({"status": "ok"})
