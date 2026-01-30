# agenda_app/cron.py
import json
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from pywebpush import webpush, WebPushException

from notificaciones_app.models import PushSubscription
from agenda_app.models import Actividad, ActividadRecordatorio


import pytz

def _actividad_datetime_inicio(a: Actividad):
    tz = pytz.timezone("America/Santo_Domingo")

    hora = a.hora_inicio or datetime.strptime("08:00", "%H:%M").time()
    dt_local = datetime.combine(a.fecha, hora)

    # Interpretar la fecha/hora como local (RD)
    dt_local = tz.localize(dt_local)

    # Convertir a UTC (para compararla con timezone.now())
    return dt_local.astimezone(pytz.UTC)


def _usuarios_de_unidad(unidad):
    """
    ✅ Resolver destinatarios sin pedirte más archivos ahora.

    Intenta el patrón más común que tú ya usas en otras partes:
    Miembro.objects.filter(membresias_unidad__unidad=unidad, estado_miembro="activo")

    Si no existe exactamente, devolvemos [] y lo ajustamos después con tu modelo real.
    """
    try:
        from miembros_app.models import Miembro
        qs = Miembro.objects.filter(membresias_unidad__unidad=unidad).distinct()
        # si existe estado_miembro, filtra activos
        if hasattr(Miembro, "estado_miembro"):
            qs = qs.filter(estado_miembro="activo")
        usuarios = []
        for m in qs:
            u = getattr(m, "usuario", None)
            if u:
                usuarios.append(u)
        return usuarios
    except Exception:
        return []


def _enviar_push_a_usuario(user, titulo, body, url="/agenda/"):
    subs = PushSubscription.objects.filter(user=user, activo=True)
    if not subs.exists():
        return {"enviados": 0, "errores": 0}

    vapid_private = getattr(settings, "VAPID_PRIVATE_KEY", "")
    vapid_subject = getattr(settings, "VAPID_CLAIMS_SUBJECT", "mailto:admin@example.com")
    if not vapid_private:
        return {"enviados": 0, "errores": 1}

    payload = json.dumps({"title": titulo, "body": body, "url": url})

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
                vapid_claims={"sub": vapid_subject},
            )
            enviados += 1
        except WebPushException as e:
            errores += 1
            if e.response and e.response.status_code in [404, 410]:
                s.activo = False
                s.save(update_fields=["activo", "actualizado_en"])

    return {"enviados": enviados, "errores": errores}


def task_recordatorios_agenda():
    """
    Task del motor para agenda:
    - Actividades PROGRAMADAS
    - Recordatorio 60 min antes (de momento)
    - Sin duplicados gracias a ActividadRecordatorio
    """
    ahora = timezone.now()
    ventana_hasta = ahora + timedelta(minutes=65)  # margen
    minutos_antes = 60

    actividades = Actividad.objects.filter(estado=Actividad.Estado.PROGRAMADA)

    enviados = 0
    errores = 0
    marcados = 0

    for a in actividades:
        dt_inicio = _actividad_datetime_inicio(a)
        dt_envio = dt_inicio - timedelta(minutes=minutos_antes)

        if not (ahora <= dt_envio <= ventana_hasta):
            continue

        rec, created = ActividadRecordatorio.objects.get_or_create(
            actividad=a,
            minutos_antes=minutos_antes,
            defaults={"enviado_en": None}
        )
        if (not created) and rec.enviado_en is not None:
            continue

        # Destinatarios
        # ✅ BROADCAST: enviar a TODAS las suscripciones activas
        subs = PushSubscription.objects.filter(activo=True)

        if not subs.exists():
            rec.enviado_en = timezone.now()
            rec.save(update_fields=["enviado_en"])
            marcados += 1
            continue

        payload = json.dumps({
            "title": "⏰ Recordatorio SOID",
            "body": f"En {minutos_antes} min: {a.titulo}",
            "url": "/agenda/",
        })

        vapid_private = getattr(settings, "VAPID_PRIVATE_KEY", "")
        vapid_subject = getattr(settings, "VAPID_CLAIMS_SUBJECT", "mailto:admin@example.com")

        for s in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": s.endpoint,
                        "keys": {"p256dh": s.p256dh, "auth": s.auth},
                    },
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={"sub": vapid_subject},
                )
                enviados += 1
            except WebPushException as e:
                errores += 1
                if e.response and e.response.status_code in [404, 410]:
                    s.activo = False
                    s.save(update_fields=["activo", "actualizado_en"])


        rec.enviado_en = timezone.now()
        rec.save(update_fields=["enviado_en"])
        marcados += 1

    return {
        "recordatorios_marcados": marcados,
        "enviados": enviados,
        "errores": errores,
        "minutos_antes": minutos_antes,
    }
