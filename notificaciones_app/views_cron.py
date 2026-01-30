# notificaciones_app/views_cron.py
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET

from .motor import ejecutar_motor

@require_GET
def cron_motor(request):
    token = request.headers.get("X-CRON-TOKEN", "")
    if token != getattr(settings, "CRON_TOKEN", ""):
        return JsonResponse({"ok": False, "error": "unauthorized"}, status=403)

    resultados = ejecutar_motor()
    return JsonResponse({
        "ok": True,
        "resultados": [
            {"nombre": r.nombre, "ok": r.ok, "detalle": r.detalle}
            for r in resultados
        ]
    })
