# notificaciones_app/views_push.py

import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from pywebpush import webpush, WebPushException
from .models import PushSubscription


@login_required
@require_GET
def push_status(request):
    """Verifica si el usuario tiene suscripciones push activas."""
    activo = PushSubscription.objects.filter(user=request.user, activo=True).exists()
    return JsonResponse({"activo": activo})

@login_required
@require_POST
def push_unsubscribe(request):
    """
    Desactiva la suscripción del dispositivo actual.
    Si no se envía endpoint, desactiva todas las del usuario.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = {}

    endpoint = (data.get("endpoint") or "").strip()
    
    if endpoint:
        # Desactivar solo la suscripción específica
        PushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint,
            activo=True
        ).update(activo=False)
    else:
        # Sin endpoint: desactivar todas las del usuario
        PushSubscription.objects.filter(
            user=request.user,
            activo=True
        ).update(activo=False)

    return JsonResponse({"ok": True})

@login_required
@require_POST
def push_subscribe(request):
    """
    Recibe y guarda una suscripción push.
    
    Espera JSON:
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

    user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:255]

    obj, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": user_agent,
            "activo": True,
        },
    )

    return JsonResponse({"ok": True, "id": obj.id})


@login_required
@require_POST
def push_test(request):
    """Envía una notificación push de prueba al usuario actual."""
    subs = PushSubscription.objects.filter(user=request.user, activo=True)

    if not subs.exists():
        return JsonResponse({"ok": False, "error": "No hay suscripciones activas."}, status=400)

    # Verificar configuración VAPID
    vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_subject = getattr(settings, 'VAPID_CLAIMS_SUBJECT', 'mailto:admin@example.com')
    
    if not vapid_private:
        return JsonResponse({"ok": False, "error": "VAPID no configurado en el servidor."}, status=500)

    payload = json.dumps({
        "title": "SOID",
        "body": "Push de prueba: ¡ya estás conectado! ✅",
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
                vapid_private_key=vapid_private,
                vapid_claims={"sub": vapid_subject},  # ✅ Corregido
            )
            enviados += 1
        except WebPushException as e:
            errores += 1
            # Si el endpoint expiró, desactivarlo
            if e.response and e.response.status_code in [404, 410]:
                s.activo = False
                s.save(update_fields=["activo", "actualizado_en"])

    return JsonResponse({"ok": True, "enviados": enviados, "errores": errores})