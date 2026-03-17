# notificaciones_app/views.py

from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import Notification


def _require_tenant(request):
    """Retorna el tenant o None si no está disponible."""
    tenant = getattr(request, 'tenant', None)
    return tenant


@login_required
def marcar_todas_leidas(request):
    """
    Marca todas las notificaciones no leídas del usuario como leídas.
    """
    tenant = _require_tenant(request)
    if not tenant:
        return HttpResponseForbidden("Tenant no disponible.")
    
    Notification.objects.filter(
        tenant=tenant,
        usuario=request.user,
        leida=False
    ).update(leida=True)
    
    return JsonResponse({"status": "ok"})