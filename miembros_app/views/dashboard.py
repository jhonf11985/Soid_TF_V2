# -*- coding: utf-8 -*-
"""
miembros_app/views/dashboard.py
Vista del dashboard principal del módulo de miembros.
"""

from datetime import date, timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q, Count
from django.utils import timezone

from miembros_app.models import Miembro
from core.utils_config import get_edad_minima_miembro_oficial

from .utils import calcular_edad, porcentaje


@login_required
@permission_required("miembros_app.view_miembro", raise_exception=True)
def miembros_dashboard(request):
    """Dashboard principal del módulo de miembros."""
    miembros = Miembro.objects.filter(activo=True)
    edad_minima = get_edad_minima_miembro_oficial()
    hoy = date.today()

    # Conteo de membresía oficial
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

    # Descarriados (inactivos)
    miembros_descarriados = Miembro.objects.filter(activo=False, razon_salida__isnull=False)
    descarriados = sum(
        1 for m in miembros_descarriados
        if calcular_edad(m.fecha_nacimiento) is not None
        and calcular_edad(m.fecha_nacimiento) >= edad_minima
        and "descarri" in str(m.razon_salida).lower()
    )

    total_oficiales = activos + pasivos + observacion + disciplina + catecumenos
    total_base = total_oficiales

    # Distribución por etapa de vida
    campo_categoria = Miembro._meta.get_field("categoria_edad")
    choices_dict = dict(campo_categoria.flatchoices)
    
    distribucion_raw = (
        miembros.values("categoria_edad")
        .exclude(categoria_edad="")
        .annotate(cantidad=Count("id"))
        .order_by("categoria_edad")
    )
    
    distribucion_etapa_vida = [
        {
            "codigo": row["categoria_edad"],
            "nombre": choices_dict.get(row["categoria_edad"], "Sin definir"),
            "cantidad": row["cantidad"],
        }
        for row in distribucion_raw
    ]

    # Próximos cumpleaños (30 días)
    fin_rango = hoy + timedelta(days=30)
    cumple_qs = miembros.filter(fecha_nacimiento__isnull=False)
    
    proximos_cumpleanos = []
    for m in cumple_qs:
        fn = m.fecha_nacimiento
        proximo = fn.replace(year=hoy.year)
        if proximo < hoy:
            proximo = proximo.replace(year=hoy.year + 1)
        
        if hoy <= proximo <= fin_rango:
            proximos_cumpleanos.append({
                "nombre": f"{m.nombres} {m.apellidos}",
                "fecha": proximo,
                "edad": proximo.year - fn.year,
            })
    
    proximos_cumpleanos.sort(key=lambda x: x["fecha"])

    # KPIs
    nuevos_mes = miembros.filter(
        fecha_ingreso_iglesia__year=hoy.year,
        fecha_ingreso_iglesia__month=hoy.month,
    ).count()

    hace_7_dias = timezone.now() - timedelta(days=7)
    nuevos_creyentes_semana = Miembro.objects.filter(
        nuevo_creyente=True, activo=True, fecha_creacion__gte=hace_7_dias
    ).count()

    try:
        miembros_recientes = miembros.order_by("-fecha_ingreso_iglesia", "-fecha_creacion")[:5]
    except Exception:
        miembros_recientes = miembros.order_by("-fecha_ingreso_iglesia", "-id")[:5]

    # Alertas de datos incompletos
    sin_contacto = miembros.filter(
        (Q(telefono__isnull=True) | Q(telefono="")),
        (Q(telefono_secundario__isnull=True) | Q(telefono_secundario="")),
        (Q(email__isnull=True) | Q(email="")),
    ).count()

    sin_foto = miembros.filter(Q(foto__isnull=True) | Q(foto="")).count()
    sin_fecha_nacimiento = miembros.filter(fecha_nacimiento__isnull=True).count()

    ultimas_salidas = (
        Miembro.objects.filter(activo=False, fecha_salida__isnull=False)
        .order_by("-fecha_salida", "apellidos", "nombres")[:5]
    )

    nuevos_creyentes_recientes = (
        Miembro.objects.filter(nuevo_creyente=True)
        .order_by("-fecha_creacion", "-id")[:5]
    )

    context = {
        "titulo_pagina": "Miembros",
        "descripcion_pagina": f"Resumen de la membresía oficial (mayores de {edad_minima} años) y distribución general.",
        "total_miembros": miembros.count(),
        "total_oficiales": total_oficiales,
        "nuevos_mes": nuevos_mes,
        "nuevos_creyentes_semana": nuevos_creyentes_semana,
        "activos": activos,
        "pasivos": pasivos,
        "descarriados": descarriados,
        "observacion": observacion,
        "disciplina": disciplina,
        "catecumenos": catecumenos,
        "pct_activos": porcentaje(activos, total_base),
        "pct_pasivos": porcentaje(pasivos, total_base),
        "pct_descarriados": porcentaje(descarriados, total_base),
        "pct_observacion": porcentaje(observacion, total_base),
        "pct_catecumenos": porcentaje(catecumenos, total_base),
        "pct_disciplina": porcentaje(disciplina, total_base),
        "distribucion_etapa_vida": distribucion_etapa_vida,
        "proximos_cumpleanos": proximos_cumpleanos,
        "miembros_recientes": miembros_recientes,
        "sin_contacto": sin_contacto,
        "sin_foto": sin_foto,
        "sin_fecha_nacimiento": sin_fecha_nacimiento,
        "ultimas_salidas": ultimas_salidas,
        "nuevos_creyentes_recientes": nuevos_creyentes_recientes,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
    }
    
    return render(request, "miembros_app/miembros_dashboard.html", context)