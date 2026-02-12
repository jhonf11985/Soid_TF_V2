from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import render
from django.utils import timezone
from miembros_app.views.utils import calcular_edad, porcentaje
from core.utils_config import get_edad_minima_miembro_oficial

from miembros_app.models import Miembro
from core.utils_config import get_edad_minima_miembro_oficial


def _cutoff_nacimiento_por_edad(edad_minima: int, hoy: date) -> date:
    try:
        return hoy.replace(year=hoy.year - edad_minima)
    except ValueError:
        return hoy.replace(month=2, day=28, year=hoy.year - edad_minima)


def _diagnostico_membresia(activos, pasivos, observacion, disciplina, catecumenos, descarriados, total):
    """
    Diagnóstico pastoral basado en la condición real de la membresía.
    No habla de números, interpreta la vida espiritual de la iglesia.
    """

    if total == 0:
        return {
            "nivel": "sin_datos",
            "titulo": "Sin base de evaluación",
            "mensaje": "Aún no hay miembros oficiales suficientes para evaluar la condición de la iglesia.",
        }

    # mayorías
    if activos >= (total * 0.75):
        return {
            "nivel": "saludable",
            "titulo": "Iglesia firme",
            "mensaje": "La congregación se mantiene estable. La mayoría camina activamente en la vida de la iglesia.",
        }

    # crecimiento fuerte
    if catecumenos >= (total * 0.35):
        return {
            "nivel": "crecimiento",
            "titulo": "Tiempo de formación",
            "mensaje": "Dios está añadiendo personas. Muchos están en proceso y necesitan acompañamiento cercano.",
        }

    # disciplina alta
    if disciplina >= (total * 0.20) or observacion >= (total * 0.25):
        return {
            "nivel": "orden",
            "titulo": "Tiempo de corrección",
            "mensaje": "La iglesia atraviesa un proceso de orden. Algunos hermanos requieren cuidado pastoral cercano.",
        }

    # enfriamiento
    if pasivos + descarriados > activos:
        return {
            "nivel": "enfriamiento",
            "titulo": "La iglesia necesita cercanía",
            "mensaje": "Hay más hermanos detenidos que caminando. Conviene acercarse, escuchar y pastorear.",
        }

    # debilitamiento serio
    if activos <= (total * 0.40):
        return {
            "nivel": "riesgo",
            "titulo": "Necesita atención pastoral",
            "mensaje": "La membresía activa es baja. Es momento de fortalecer, visitar y recuperar.",
        }

    # neutro
    return {
        "nivel": "atencion",
        "titulo": "Momento de cuidado",
        "mensaje": "La iglesia se mantiene, pero algunos hermanos necesitan ser acompañados más de cerca.",
    }


@login_required
def inicio(request):
    """
    Centro Ejecutivo · Inicio (Nivel 1)
    - KPIs de miembros (con la MISMA lógica del dashboard de miembros)
    - Diagnóstico basado en miembros oficiales
    - Focos principales (limpios)
    """
    miembros = Miembro.objects.filter(activo=True)
    edad_minima = get_edad_minima_miembro_oficial()
    hoy = date.today()

    # ============================================================
    # 1) CONTEO DE MEMBRESÍA OFICIAL (MISMA LÓGICA QUE MIEMBROS)
    # ============================================================
    activos = pasivos = observacion = disciplina = catecumenos = 0

    for m in miembros:
        edad = calcular_edad(m.fecha_nacimiento)
        if edad is None or edad < edad_minima:
            continue
        if m.nuevo_creyente:
            continue
        if not m.bautizado_confirmado:
            catecumenos += 1
            continue

        if m.estado_miembro == "activo":
            activos += 1
        elif m.estado_miembro == "pasivo":
            pasivos += 1
        elif m.estado_miembro == "observacion":
            observacion += 1
        elif m.estado_miembro == "disciplina":
            disciplina += 1

    # Descarriados (inactivos) — MISMA LÓGICA
    miembros_descarriados = Miembro.objects.filter(activo=False, razon_salida__isnull=False)
    descarriados = sum(
        1 for m in miembros_descarriados
        if calcular_edad(m.fecha_nacimiento) is not None
        and calcular_edad(m.fecha_nacimiento) >= edad_minima
        and "descarri" in str(m.razon_salida).lower()
    )

    total_oficiales = activos + pasivos + observacion + disciplina + catecumenos
    total_base = total_oficiales  # igual que tu dashboard

    # ============================================================
    # 2) DIAGNÓSTICO EJECUTIVO (solo oficiales)
    # ============================================================
    ratio_activos = (activos / total_oficiales) if total_oficiales else 0.0

    diag = _diagnostico_membresia(
        activos,
        pasivos,
        observacion,
        disciplina,
        catecumenos,
        descarriados,
        total_oficiales
    )

    desglose_no_activos = []
    # Aquí mostramos solo oficiales NO activos (como “por qué” en 1 línea)
    if catecumenos:
        desglose_no_activos.append({"label": "Catecúmenos", "value": catecumenos})
    if pasivos:
        desglose_no_activos.append({"label": "Pasivos", "value": pasivos})
    if observacion:
        desglose_no_activos.append({"label": "Observación", "value": observacion})
    if disciplina:
        desglose_no_activos.append({"label": "Disciplina", "value": disciplina})

    # ============================================================
    # 3) KPIs “ejecutivos” (alineados con tu dashboard)
    # ============================================================
    total_miembros_registrados = miembros.count()  # activo=True (incluye niños y nuevos creyentes) :contentReference[oaicite:1]{index=1}

    hace_7_dias = timezone.now() - timedelta(days=7)
    nuevos_creyentes_semana = Miembro.objects.filter(
        nuevo_creyente=True, activo=True, fecha_creacion__gte=hace_7_dias
    ).count()  # igual que tu dashboard :contentReference[oaicite:2]{index=2}

    # ============================================================
    # 4) FOCOS PRINCIPALES (Nivel 1, sin listas largas)
    #    (aquí puedes ajustar qué entra como foco)
    # ============================================================
    focos = []

    # Foco: Nuevos creyentes sin mentor
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

    # Foco: Datos incompletos (igual espíritu del dashboard)
    sin_contacto = miembros.filter(
        (Q(telefono__isnull=True) | Q(telefono="")),
        (Q(telefono_secundario__isnull=True) | Q(telefono_secundario="")),
        (Q(email__isnull=True) | Q(email="")),
    ).count()

    if sin_contacto:
        focos.append({
            "nivel": "media",
            "titulo": "Registros sin contacto",
            "detalle": f"{sin_contacto} miembros sin teléfono(s) y sin email.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=sin_contacto",
        })

    # Foco: Oficiales fuera de activo (resumen ejecutivo)
    oficiales_no_activos = total_oficiales - activos
    if total_oficiales and oficiales_no_activos:
        focos.append({
            "nivel": "media" if ratio_activos >= 0.70 else "alta",
            "titulo": "Miembros oficiales fuera de activo",
            "detalle": f"{oficiales_no_activos} oficiales no están en estado pastoral activo.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=oficiales_no_activos",
        })

    # Mensaje general
    if not focos:
        estado_general = "Todo se ve estable. No hay focos críticos ahora mismo."
    else:
        estado_general = f"Hay {len(focos)} foco(s) que merecen atención."

    context = {
        "estado_general": estado_general,

        # KPIs estilo “miembros_dashboard”
        "kpis": [
            {"label": "Miembros registrados", "value": total_miembros_registrados, "sub": "Incluye niños y nuevos creyentes"},
            {"label": "Miembros oficiales", "value": total_oficiales, "sub": f"Mayores de {edad_minima} años"},
            {"label": "Nuevos creyentes", "value": nuevos_creyentes_semana, "sub": "Últimos 7 días"},
            {"label": "Descarriados", "value": descarriados, "sub": "Necesitan seguimiento"},
        ],

        # Membresía (tarjeta de diagnóstico)
        "membresia": {
            "oficiales_total": total_oficiales,
            "oficiales_estado_activo": activos,
            "ratio": ratio_activos,
            "diag": diag,
            "desglose_no_activos": desglose_no_activos,
            "cta_url": "/ejecutivo/personas/?filtro=oficiales_no_activos",
        },

        # Estados (por si luego quieres mostrar mini-cards)
        "estados": {
            "activos": activos,
            "pasivos": pasivos,
            "observacion": observacion,
            "disciplina": disciplina,
            "catecumenos": catecumenos,
            "descarriados": descarriados,
            "pct_activos": porcentaje(activos, total_base),
            "pct_pasivos": porcentaje(pasivos, total_base),
            "pct_observacion": porcentaje(observacion, total_base),
            "pct_disciplina": porcentaje(disciplina, total_base),
            "pct_catecumenos": porcentaje(catecumenos, total_base),
        },

        # Focos principales (máximo 5)
        "focos": focos[:5],
    }

    return render(request, "ejecutivo_app/inicio.html", context)


@login_required
def personas(request):
    # Placeholder del Nivel 2 (lo haremos luego)
    return render(request, "ejecutivo_app/personas.html", {})
