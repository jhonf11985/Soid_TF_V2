from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from miembros_app.models import Miembro
from core.utils_config import get_edad_minima_miembro_oficial


def _cutoff_nacimiento_por_edad(edad_minima: int, hoy: date) -> date:
    """
    Fecha límite de nacimiento para tener al menos 'edad_minima'.
    Ej: si edad_minima=12, y hoy=2026-02-12 -> cutoff ~ 2014-02-12
    """
    try:
        return hoy.replace(year=hoy.year - edad_minima)
    except ValueError:
        # Manejo de 29 de Feb
        # si hoy es 29/02 y el año objetivo no tiene 29, usamos 28/02
        return hoy.replace(month=2, day=28, year=hoy.year - edad_minima)


@login_required
def inicio(request):
    hoy = timezone.localdate()

    # -----------------------------
    # CONTADORES (Foto rápida)
    # -----------------------------
    total = Miembro.objects.count()
    activos = Miembro.objects.filter(activo=True).count()
    nuevos_creyentes = Miembro.objects.filter(nuevo_creyente=True, activo=True).count()

    # "Miembros oficiales" aproximado por reglas (bautizado_confirmado + edad >= mínima)
    edad_min = get_edad_minima_miembro_oficial()
    cutoff = _cutoff_nacimiento_por_edad(edad_min, hoy)
    miembros_oficiales = Miembro.objects.filter(
        activo=True,
        bautizado_confirmado=True,
        fecha_nacimiento__isnull=False,
        fecha_nacimiento__lte=cutoff,
        nuevo_creyente=False,
    ).count()

    inactivos = Miembro.objects.filter(activo=False).count()

    # -----------------------------
    # ALERTAS PRINCIPALES (Focos)
    # -----------------------------
    focos = []

    # 1) Nuevos creyentes sin mentor
    nc_sin_mentor = Miembro.objects.filter(
        activo=True,
        nuevo_creyente=True
    ).filter(Q(mentor__isnull=True) | Q(mentor="")).count()

    if nc_sin_mentor:
        focos.append({
            "nivel": "alta",
            "titulo": "Nuevos creyentes sin mentor",
            "detalle": f"{nc_sin_mentor} requieren asignación.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=nc_sin_mentor",
        })

    # 2) Estados pastorales sensibles
    estados_sensibles = ["disciplina", "observacion", "descarriado", "pasivo"]
    sensibles = Miembro.objects.filter(
        activo=True,
        estado_miembro__in=estados_sensibles
    ).count()

    if sensibles:
        focos.append({
            "nivel": "alta",
            "titulo": "Estados pastorales sensibles",
            "detalle": f"{sensibles} personas en disciplina/observación/descarriado/pasivo.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=estado_sensible",
        })

    # 3) Reingresos pendientes (reincorporado sin estado pastoral definido)
    reingresos_pend = Miembro.objects.filter(
        activo=True,
        etapa_actual="reincorporado"
    ).filter(Q(estado_pastoral_reingreso__isnull=True) | Q(estado_pastoral_reingreso="")).count()

    if reingresos_pend:
        focos.append({
            "nivel": "media",
            "titulo": "Reingresos pendientes de cierre",
            "detalle": f"{reingresos_pend} reincorporaciones sin definir estado pastoral.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=reingresos_pend",
        })

    # 4) Fichas incompletas (contacto/edad)
    fichas_incompletas = Miembro.objects.filter(activo=True).filter(
        Q(telefono_norm__isnull=True) | Q(telefono_norm="") |
        Q(fecha_nacimiento__isnull=True)
    ).count()

    if fichas_incompletas:
        focos.append({
            "nivel": "media",
            "titulo": "Fichas incompletas",
            "detalle": f"{fichas_incompletas} sin teléfono normalizado o sin fecha de nacimiento.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=fichas_incompletas",
        })

    # 5) Salidas recientes (últimos 30 días)
    hace_30 = hoy - timedelta(days=30)
    salidas_recientes = Miembro.objects.filter(
        fecha_salida__isnull=False,
        fecha_salida__gte=hace_30
    ).count()

    if salidas_recientes:
        focos.append({
            "nivel": "baja",
            "titulo": "Salidas recientes (30 días)",
            "detalle": f"{salidas_recientes} salidas registradas recientemente.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=salidas_recientes",
        })

    # Mensaje ejecutivo corto
    if not focos:
        estado_general = "Todo se ve estable. No hay focos críticos ahora mismo."
    else:
        estado_general = f"Hay {len(focos)} foco(s) que merecen atención."

    context = {
        "estado_general": estado_general,
        "kpis": [
            {"label": "Total registrados", "value": total},
            {"label": "Activos", "value": activos},
            {"label": "Nuevos creyentes", "value": nuevos_creyentes},
            {"label": "Miembros oficiales", "value": miembros_oficiales},
            {"label": "Inactivos", "value": inactivos},
        ],
        "focos": focos[:5],  # máximo 5
    }
    return render(request, "ejecutivo_app/inicio.html", context)


@login_required
def personas(request):
    # Placeholder del Nivel 2 (lo haremos luego)
    return render(request, "ejecutivo_app/personas.html", {})
