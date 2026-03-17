# notificaciones_app/views_cron.py

from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET

from tenants.models import Tenant
from .motor import ejecutar_motor


@require_GET
def cron_motor(request):
    """
    Ejecuta el motor de notificaciones para todos los tenants activos.
    Requiere autenticación vía X-CRON-TOKEN.
    """
    token = request.headers.get("X-CRON-TOKEN", "")
    if token != getattr(settings, "CRON_TOKEN", ""):
        return JsonResponse({"ok": False, "error": "unauthorized"}, status=403)

    todos_resultados = []
    
    # Iterar por cada tenant activo
    for tenant in Tenant.objects.filter(activo=True):
        resultados = ejecutar_motor(tenant=tenant)
        for r in resultados:
            todos_resultados.append({
                "tenant": tenant.nombre,
                "nombre": r.nombre,
                "ok": r.ok,
                "detalle": r.detalle,
            })
    
    return JsonResponse({
        "ok": True,
        "resultados": todos_resultados,
    })