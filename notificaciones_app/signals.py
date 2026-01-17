# notificaciones_app/signals.py

import json
import logging
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from pywebpush import webpush, WebPushException

from .models import Notification, PushSubscription

logger = logging.getLogger(__name__)


def enviar_push_a_usuario(usuario, titulo, mensaje, url="/", badge_count=0):
    """
    Envía notificación push a todas las suscripciones activas del usuario.
    
    Args:
        usuario: User instance
        titulo: Título de la notificación
        mensaje: Cuerpo del mensaje
        url: URL a abrir al hacer clic
        badge_count: Número para mostrar en el badge del icono
    
    Returns:
        dict con 'enviados' y 'errores'
    """
    suscripciones = PushSubscription.objects.filter(user=usuario, activo=True)
    
    if not suscripciones.exists():
        logger.debug(f"[Push] Usuario {usuario} no tiene suscripciones activas")
        return {"enviados": 0, "errores": 0}
    
    # Verificar que tenemos las claves VAPID
    vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_subject = getattr(settings, 'VAPID_CLAIMS_SUBJECT', 'mailto:admin@example.com')
    
    if not vapid_private:
        logger.error("[Push] VAPID_PRIVATE_KEY no configurada")
        return {"enviados": 0, "errores": 0}
    
    payload = json.dumps({
        "title": titulo,
        "body": mensaje,
        "url": url,
        "badge_count": badge_count,
    })
    
    enviados = 0
    errores = 0
    
    for sub in suscripciones:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    },
                },
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims={"sub": vapid_subject},
            )
            enviados += 1
            logger.debug(f"[Push] Enviado a {usuario} (endpoint: {sub.endpoint[:50]}...)")
            
        except WebPushException as e:
            errores += 1
            logger.warning(f"[Push] Error enviando a {usuario}: {e}")
            
            # Si el endpoint ya no es válido (410 Gone, 404 Not Found), desactivar
            if e.response and e.response.status_code in [404, 410]:
                sub.activo = False
                sub.save(update_fields=["activo", "actualizado_en"])
                logger.info(f"[Push] Suscripción desactivada (status {e.response.status_code})")
                
        except Exception as e:
            errores += 1
            logger.error(f"[Push] Error inesperado: {e}")
    
    return {"enviados": enviados, "errores": errores}


@receiver(post_save, sender=Notification)
def enviar_push_al_crear_notificacion(sender, instance, created, **kwargs):
    """
    Signal que se ejecuta automáticamente cuando se crea una Notification.
    Envía push al usuario correspondiente.
    """
    if not created:
        # Solo enviar push cuando se CREA, no cuando se actualiza
        return
    
    # Contar notificaciones no leídas para el badge
    no_leidas = Notification.objects.filter(
        usuario=instance.usuario,
        leida=False
    ).count()
    
    # Enviar push
    resultado = enviar_push_a_usuario(
        usuario=instance.usuario,
        titulo=instance.titulo,
        mensaje=instance.mensaje or "",
        url=instance.url_destino or "/",
        badge_count=no_leidas,
    )
    
    if resultado["enviados"] > 0:
        logger.info(
            f"[Push] Notificación '{instance.titulo}' enviada a {instance.usuario} "
            f"({resultado['enviados']} dispositivos)"
        )