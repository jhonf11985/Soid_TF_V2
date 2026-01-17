import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from pywebpush import webpush, WebPushException
from .models import PushSubscription


def _get_user_agent(request) -> str:
    return (request.META.get("HTTP_USER_AGENT") or "")[:255]


@login_required
@require_GET
def push_status(request):
    activo = PushSubscription.objects.filter(user=request.user, activo=True).exists()
    return JsonResponse({"activo": activo})


@login_required
@require_POST
def push_unsubscribe(request):
    PushSubscription.objects.filter(user=request.user, activo=True).update(activo=False)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def push_subscribe(request):
    """
    Recibe:
    {
      "endpoint": "...",
      "expirationTime": null,
      "keys": {"p256dh": "...", "auth": "..."}
    }
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

    endpoint = (data.get("endpoint") or "").strip()
    keys = data.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth = (keys.get("auth") or "").strip()

    if not endpoint or not p256dh or not auth:
        return JsonResponse({"ok": False, "error": "Faltan datos de suscripción."}, status=400)

    ua = (request.META.get("HTTP_USER_AGENT") or "")[:255]

    obj, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": ua,
            "activo": True,
        },
    )

    return JsonResponse({"ok": True, "id": obj.id})




@login_required
@require_POST
def push_test(request):
    subs = PushSubscription.objects.filter(user=request.user, activo=True)

    if not subs.exists():
        return JsonResponse({"ok": False, "error": "No hay suscripciones activas."}, status=400)

    payload = json.dumps({
        "title": "SOID",
        "body": "Push de prueba: ya estás conectado ✅",
        "url": "/",
    })

    enviados = 0
    errores = 0

    for s in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": s.endpoint,
                    "keys": {"p256dh": s.p256dh, "auth": s.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIMS_SUBJECT},
            )
            enviados += 1
        except WebPushException:
            errores += 1
            # Si falla por endpoint viejo, lo desactivamos para limpiar
            s.activo = False
            s.save(update_fields=["activo", "actualizado_en"])

    return JsonResponse({"ok": True, "enviados": enviados, "errores": errores})