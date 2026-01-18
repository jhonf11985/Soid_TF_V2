# notificaciones_app/utils.py

from django.urls import reverse, NoReverseMatch
from .models import Notification

# notificaciones_app/utils.py

import json
from django.conf import settings
from pywebpush import webpush, WebPushException
from django.urls import reverse, NoReverseMatch
from .models import Notification


def crear_notificacion(
    usuario,
    titulo,
    mensaje="",
    url_name=None,
    tipo="info",
):
    """
    Crea una notificación para un usuario.

    - usuario: instancia de User (request.user, por ejemplo)
    - titulo: texto corto que se mostrará en la lista
    - mensaje: texto más largo (opcional)
    - url_name: nombre de URL de Django, por ejemplo "miembros_app:dashboard"
                Si no se puede resolver, se guarda tal cual (por si es una ruta absoluta).
    - tipo: "info", "success", "warning", "error"
    """

    url_destino = ""

    if url_name:
        try:
            # Intentamos resolver el nombre de URL a una ruta real
            url_destino = reverse(url_name)
        except NoReverseMatch:
            # Si falla, guardamos el valor tal cual (por si es un path directo)
            url_destino = url_name

    return Notification.objects.create(
        usuario=usuario,
        titulo=titulo,
        mensaje=mensaje,
        url_destino=url_destino,
        tipo=tipo,
    )


def enviar_push_notification(suscripcion, titulo, mensaje, url="/"):
    """
    Envía una notificación push a una suscripción específica.
    
    Args:
        suscripcion: instancia de PushSubscription
        titulo: título de la notificación
        mensaje: cuerpo del mensaje
        url: URL de destino al hacer clic
    
    Returns:
        True si se envió correctamente, False si hubo error
    """
    vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_subject = getattr(settings, 'VAPID_CLAIMS_SUBJECT', 'mailto:admin@example.com')
    
    if not vapid_private:
        raise ValueError("VAPID no configurado en el servidor")
    
    payload = json.dumps({
        "title": titulo,
        "body": mensaje,
        "url": url,
    })
    
    try:
        webpush(
            subscription_info={
                "endpoint": suscripcion.endpoint,
                "keys": {"p256dh": suscripcion.p256dh, "auth": suscripcion.auth},
            },
            data=payload,
            vapid_private_key=vapid_private,
            vapid_claims={"sub": vapid_subject},
        )
        return True
    except WebPushException as e:
        # Si el endpoint expiró, desactivarlo
        if e.response and e.response.status_code in [404, 410]:
            suscripcion.activo = False
            suscripcion.save(update_fields=["activo", "actualizado_en"])
        return False
def crear_notificacion(
    usuario,
    titulo,
    mensaje="",
    url_name=None,
    tipo="info",
):
    """
    Crea una notificación para un usuario.

    - usuario: instancia de User (request.user, por ejemplo)
    - titulo: texto corto que se mostrará en la lista
    - mensaje: texto más largo (opcional)
    - url_name: nombre de URL de Django, por ejemplo "miembros_app:dashboard"
                Si no se puede resolver, se guarda tal cual (por si es una ruta absoluta).
    - tipo: "info", "success", "warning", "error"
    """

    url_destino = ""

    if url_name:
        try:
            # Intentamos resolver el nombre de URL a una ruta real
            url_destino = reverse(url_name)
        except NoReverseMatch:
            # Si falla, guardamos el valor tal cual (por si es un path directo)
            url_destino = url_name

    return Notification.objects.create(
        usuario=usuario,
        titulo=titulo,
        mensaje=mensaje,
        url_destino=url_destino,
        tipo=tipo,
    )
