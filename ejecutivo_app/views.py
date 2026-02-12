from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import render
from django.utils import timezone

from miembros_app.models import Miembro
from core.utils_config import get_edad_minima_miembro_oficial


def _cutoff_nacimiento_por_edad(edad_minima: int, hoy: date) -> date:
    try:
        return hoy.replace(year=hoy.year - edad_minima)
    except ValueError:
        return hoy.replace(month=2, day=28, year=hoy.year - edad_minima)


def _diagnostico_membresia(ratio: float) -> dict:
    """
    ratio = oficiales_activos / oficiales_total
    Devuelve nivel + mensaje ejecutivo.
    """
    if ratio >= 0.85:
        return {
            "nivel": "saludable",
            "titulo": "Membresía saludable",
            "mensaje": "La mayoría de los miembros oficiales está en estado pastoral activo.",
        }
    if ratio >= 0.70:
        return {
            "nivel": "atencion",
            "titulo": "Membresía en atención",
            "mensaje": "Hay una porción importante de oficiales fuera de activo. Conviene revisar pasivos y observación.",
        }
    if ratio >= 0.50:
        return {
            "nivel": "preocupante",
            "titulo": "Membresía preocupante",
            "mensaje": "Muchos oficiales no están en estado activo. Recomiendo revisar causas y activar seguimiento.",
        }
    return {
        "nivel": "critico",
        "titulo": "Membresía en estado crítico",
        "mensaje": "La proporción de oficiales activos es baja. Recomiendo un plan pastoral de recuperación.",
    }


@login_required
def inicio(request):
    hoy = timezone.localdate()

    # -----------------------------
    # KPIs básicos (foto rápida)
    # -----------------------------
    total = Miembro.objects.count()
    activos_pertenencia = Miembro.objects.filter(activo=True).count()  # pertenece a la iglesia (checkbox)
    nuevos_creyentes = Miembro.objects.filter(nuevo_creyente=True, activo=True).count()
    inactivos_pertenencia = Miembro.objects.filter(activo=False).count()

    # -----------------------------
    # OFICIALES (base del diagnóstico)
    # -----------------------------
    edad_min = get_edad_minima_miembro_oficial()
    cutoff = _cutoff_nacimiento_por_edad(edad_min, hoy)

    oficiales_qs = Miembro.objects.filter(
        activo=True,                  # sigue perteneciendo
        nuevo_creyente=False,
        bautizado_confirmado=True,
        fecha_nacimiento__isnull=False,
        fecha_nacimiento__lte=cutoff,
    )

    oficiales_total = oficiales_qs.count()

    # Estado pastoral "activo" (no el checkbox)
    oficiales_estado_activo = oficiales_qs.filter(estado_miembro="activo").count()

    ratio = (oficiales_estado_activo / oficiales_total) if oficiales_total else 0.0
    diag = _diagnostico_membresia(ratio) if oficiales_total else {
        "nivel": "sin_datos",
        "titulo": "Sin base de membresía oficial",
        "mensaje": "Aún no hay miembros oficiales suficientes para evaluar la salud de la membresía.",
    }

    # Desglose (solo oficiales NO activos)
    desglose_no_activos = []
    if oficiales_total:
        estados = ["pasivo", "observacion", "disciplina", "descarriado", "catecumeno", "trasladado", ""]
        counts = (
            oficiales_qs
            .exclude(estado_miembro="activo")
            .values("estado_miembro")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        mapa = {x["estado_miembro"]: x["c"] for x in counts}

        etiquetas = {
            "pasivo": "Pasivos",
            "observacion": "Observación",
            "disciplina": "Disciplina",
            "descarriado": "Descarriados",
            "catecumeno": "Catecúmenos",
            "trasladado": "Trasladados",
            "": "Sin estado",
        }

        for key in estados:
            if key in mapa and mapa[key] > 0:
                desglose_no_activos.append({"label": etiquetas.get(key, key), "value": mapa[key]})

    # -----------------------------
    # ALERTAS PRINCIPALES (Focos)
    # -----------------------------
    focos = []

    nc_sin_mentor = Miembro.objects.filter(
        activo=True, nuevo_creyente=True
    ).filter(Q(mentor__isnull=True) | Q(mentor="")).count()
    if nc_sin_mentor:
        focos.append({
            "nivel": "alta",
            "titulo": "Nuevos creyentes sin mentor",
            "detalle": f"{nc_sin_mentor} requieren asignación.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=nc_sin_mentor",
        })

    estados_sensibles = ["disciplina", "observacion", "descarriado", "pasivo"]
    sensibles = Miembro.objects.filter(activo=True, estado_miembro__in=estados_sensibles).count()
    if sensibles:
        focos.append({
            "nivel": "alta",
            "titulo": "Estados pastorales sensibles",
            "detalle": f"{sensibles} personas en disciplina/observación/descarriado/pasivo.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=estado_sensible",
        })

    reingresos_pend = Miembro.objects.filter(
        activo=True, etapa_actual="reincorporado"
    ).filter(Q(estado_pastoral_reingreso__isnull=True) | Q(estado_pastoral_reingreso="")).count()
    if reingresos_pend:
        focos.append({
            "nivel": "media",
            "titulo": "Reingresos pendientes de cierre",
            "detalle": f"{reingresos_pend} reincorporaciones sin definir estado pastoral.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=reingresos_pend",
        })

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

    hace_30 = hoy - timedelta(days=30)
    salidas_recientes = Miembro.objects.filter(fecha_salida__isnull=False, fecha_salida__gte=hace_30).count()
    if salidas_recientes:
        focos.append({
            "nivel": "baja",
            "titulo": "Salidas recientes (30 días)",
            "detalle": f"{salidas_recientes} salidas registradas recientemente.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=salidas_recientes",
        })

    # Mensaje general
    if not focos:
        estado_general = "Todo se ve estable. No hay focos críticos ahora mismo."
    else:
        estado_general = f"Hay {len(focos)} foco(s) que merecen atención."

    context = {
        "estado_general": estado_general,
        "kpis": [
            {"label": "Total registrados", "value": total},
            {"label": "Pertenecen (activo)", "value": activos_pertenencia},
            {"label": "Nuevos creyentes", "value": nuevos_creyentes},
            {"label": "Inactivos", "value": inactivos_pertenencia},
        ],
        "membresia": {
            "oficiales_total": oficiales_total,
            "oficiales_estado_activo": oficiales_estado_activo,
            "ratio": ratio,  # 0..1
            "diag": diag,
            "desglose_no_activos": desglose_no_activos,
            "cta_url": "/ejecutivo/personas/?filtro=oficiales_no_activos",
        },
        "focos": focos[:5],
    }
    return render(request, "ejecutivo_app/inicio.html", context)
@login_required
def personas(request):
    return render(request, "ejecutivo_app/personas.html", {})
