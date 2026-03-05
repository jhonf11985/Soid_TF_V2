# ia_app/services/nl_query.py
from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import FieldDoesNotExist

from .intents import (
    parse_intent,
    INTENT_ULTIMOS_MIEMBROS,
    INTENT_MIEMBROS_HOY,
    INTENT_MIEMBROS_SEMANA,
    INTENT_MIEMBROS_MES,
    INTENT_BUSCAR_NOMBRE,
    INTENT_UNKNOWN,
)

from miembros_app.models import Miembro


@dataclass
class NLResult:
    ok: bool
    intent: str
    message: str
    data: Dict[str, Any]


def _get_date_field() -> str:
    """
    Campo configurable para fecha de registro.
    """
    preferred = getattr(settings, "SOID_ASSIST_MIEMBRO_DATE_FIELD", "fecha_ingreso_iglesia")

    # Validar que exista en el modelo
    try:
        Miembro._meta.get_field(preferred)
        return preferred
    except FieldDoesNotExist:
        # fallback a nombres comunes (por si acaso)
        for fallback in ("fecha_ingreso_iglesia", "fecha_ingreso", "created_at", "creado_en"):
            try:
                Miembro._meta.get_field(fallback)
                return fallback
            except FieldDoesNotExist:
                continue

    # Si nada existe, devolvemos el preferred para que el error sea explícito
    return preferred


def _serialize(miembros_qs, date_field: str) -> List[Dict[str, Any]]:
    """
    Serializa campos básicos para respuesta JSON.
    """
    fields = ["id", "nombres", "apellidos", date_field]
    return list(miembros_qs.values(*fields))


def run_natural_query(*, tenant, user, text: str) -> NLResult:
    parsed = parse_intent(text)
    limit = int(parsed.params.get("limit") or 10)

    date_field = _get_date_field()
    qs_base = Miembro.objects.filter(tenant=tenant)

    # ✅ 1) Últimos miembros
    if parsed.intent == INTENT_ULTIMOS_MIEMBROS:
        miembros = qs_base.order_by(f"-{date_field}")[:limit]
        data = _serialize(miembros, date_field)
        return NLResult(True, parsed.intent, f"Aquí tienes los {len(data)} miembros más recientes.", {"miembros": data, "date_field": date_field})

    # ✅ 2) Miembros hoy/ayer
    if parsed.intent == INTENT_MIEMBROS_HOY:
        rng = parsed.params.get("range", "today")
        today = timezone.localdate()
        day = today - timedelta(days=1) if rng == "yesterday" else today

        filtros = {date_field: day}
        miembros = qs_base.filter(**filtros).order_by(f"-{date_field}")[:limit]
        data = _serialize(miembros, date_field)
        etiqueta = "ayer" if rng == "yesterday" else "hoy"
        return NLResult(True, parsed.intent, f"Registrados {etiqueta}: {len(data)}", {"miembros": data, "date_field": date_field})

    # ✅ 3) Miembros esta semana (lunes-domingo)
    if parsed.intent == INTENT_MIEMBROS_SEMANA:
        today = timezone.localdate()
        start = today - timedelta(days=today.weekday())  # lunes
        end = start + timedelta(days=6)

        filtros = {f"{date_field}__range": (start, end)}
        miembros = qs_base.filter(**filtros).order_by(f"-{date_field}")[:limit]
        data = _serialize(miembros, date_field)
        return NLResult(True, parsed.intent, f"Registrados esta semana: {len(data)}", {"miembros": data, "date_field": date_field})

    # ✅ 4) Miembros este mes
    if parsed.intent == INTENT_MIEMBROS_MES:
        today = timezone.localdate()
        start = today.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)

        filtros = {f"{date_field}__range": (start, end)}
        miembros = qs_base.filter(**filtros).order_by(f"-{date_field}")[:limit]
        data = _serialize(miembros, date_field)
        return NLResult(True, parsed.intent, f"Registrados este mes: {len(data)}", {"miembros": data, "date_field": date_field})

    # ✅ 5) Buscar por nombre (básico)
    if parsed.intent == INTENT_BUSCAR_NOMBRE:
        q = (parsed.params.get("q") or "").strip()
        if not q:
            return NLResult(False, parsed.intent, "Escribe un nombre para buscar.", {})

        miembros = qs_base.filter(
            nombres__icontains=q
        ).order_by("apellidos", "nombres")[:limit]

        data = _serialize(miembros, date_field)
        return NLResult(True, parsed.intent, f"Encontré {len(data)} coincidencias.", {"miembros": data, "q": q, "date_field": date_field})

    # ❌ No reconocido
    return NLResult(
        False,
        INTENT_UNKNOWN,
        "No entendí. Prueba con: 'últimos miembros registrados', 'registrados hoy', 'esta semana', 'este mes', o 'busca Juan'.",
        {"normalized": parsed.normalized, "confidence": parsed.confidence},
    )