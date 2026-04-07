# -*- coding: utf-8 -*-
"""
miembros_app/views/reportes_nuevos.py
Reportes adicionales: Aniversarios, Sectores, Bautismos, Reingresos, Ministeriales, Atención Pastoral
"""

from datetime import date, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth, ExtractDay

from miembros_app.models import (
    Miembro, 
    HogarFamiliar, 
    HogarMiembro,
    CATEGORIA_EDAD_CHOICES,
    ESTADO_MIEMBRO_CHOICES,
)
from core.models import ConfiguracionSistema

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE: ANIVERSARIOS DE MEMBRESÍA
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def reporte_aniversarios_membresia(request):
    """
    Reporte de aniversarios de membresía (fecha_ingreso_iglesia) por mes.
    Muestra cuántos años cumple cada miembro en la iglesia.
    """
    CFG = ConfiguracionSistema.load(request.tenant)
    hoy = timezone.localdate()

    # Mes seleccionado
    mes_str = request.GET.get("mes", "").strip()
    mes = int(mes_str) if mes_str.isdigit() and 1 <= int(mes_str) <= 12 else hoy.month
    anio = hoy.year

    solo_activos = request.GET.get("solo_activos", "1") == "1"
    nombre_mes = MESES_ES.get(mes, "")

    # Miembros con fecha de ingreso en ese mes
    miembros = Miembro.objects.filter(
        tenant=request.tenant,
        fecha_ingreso_iglesia__isnull=False,
        fecha_ingreso_iglesia__month=mes,
        nuevo_creyente=False,
    )

    if solo_activos:
        miembros = miembros.filter(activo=True)

    miembros = (
        miembros
        .annotate(dia=ExtractDay("fecha_ingreso_iglesia"))
        .order_by("dia", "apellidos", "nombres")
    )

    # Calcular años en la iglesia
    for m in miembros:
        if m.fecha_ingreso_iglesia:
            años = anio - m.fecha_ingreso_iglesia.year
            # Si aún no ha llegado el día del aniversario este año
            if (mes, hoy.day) < (m.fecha_ingreso_iglesia.month, m.fecha_ingreso_iglesia.day):
                años -= 1
            m.anios_membresia = años + 1  # Años que cumplirá
        else:
            m.anios_membresia = None

    context = {
        "miembros": miembros,
        "mes": mes,
        "anio": anio,
        "nombre_mes": nombre_mes,
        "solo_activos": solo_activos,
        "total": miembros.count(),
        "CFG": CFG,
    }

    return render(request, "miembros_app/reportes/aniversarios_membresia.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE: MIEMBROS POR SECTOR/ZONA
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def reporte_por_sector(request):
    """
    Reporte de miembros agrupados por sector y ciudad.
    """
    CFG = ConfiguracionSistema.load(request.tenant)

    solo_activos = request.GET.get("solo_activos", "1") == "1"
    sector_filtro = request.GET.get("sector", "").strip()
    ciudad_filtro = request.GET.get("ciudad", "").strip()

    miembros = Miembro.objects.filter(
        tenant=request.tenant,
        nuevo_creyente=False,
    )

    if solo_activos:
        miembros = miembros.filter(activo=True)

    if sector_filtro:
        miembros = miembros.filter(sector__icontains=sector_filtro)

    if ciudad_filtro:
        miembros = miembros.filter(ciudad=ciudad_filtro)

    # Agrupar por sector y ciudad
    miembros = miembros.order_by("ciudad", "sector", "apellidos", "nombres")

    # Estadísticas por sector
    stats_sector = (
        Miembro.objects.filter(
            tenant=request.tenant,
            nuevo_creyente=False,
            activo=True if solo_activos else Q(),
        )
        .exclude(sector="")
        .values("sector", "ciudad")
        .annotate(total=Count("id"))
        .order_by("ciudad", "sector")
    )

    # Lista de ciudades únicas para el filtro
    ciudades = (
        Miembro.objects.filter(tenant=request.tenant)
        .exclude(ciudad="")
        .values_list("ciudad", flat=True)
        .distinct()
        .order_by("ciudad")
    )

    # Lista de sectores únicos
    sectores = (
        Miembro.objects.filter(tenant=request.tenant)
        .exclude(sector="")
        .values_list("sector", flat=True)
        .distinct()
        .order_by("sector")
    )

    context = {
        "miembros": miembros,
        "stats_sector": stats_sector,
        "ciudades": ciudades,
        "sectores": sectores,
        "sector_filtro": sector_filtro,
        "ciudad_filtro": ciudad_filtro,
        "solo_activos": solo_activos,
        "total": miembros.count(),
        "CFG": CFG,
    }

    return render(request, "miembros_app/reportes/por_sector.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE: BAUTISMOS DEL AÑO
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def reporte_bautismos(request):
    """
    Reporte de bautismos por año, con opción de filtrar por mes.
    """
    CFG = ConfiguracionSistema.load(request.tenant)
    hoy = timezone.localdate()

    # Año seleccionado
    anio_str = request.GET.get("anio", "").strip()
    anio = int(anio_str) if anio_str.isdigit() else hoy.year

    mes_str = request.GET.get("mes", "").strip()
    mes = int(mes_str) if mes_str.isdigit() and 1 <= int(mes_str) <= 12 else None

    solo_activos = request.GET.get("solo_activos", "1") == "1"

    miembros = Miembro.objects.filter(
        tenant=request.tenant,
        fecha_bautismo__isnull=False,
        fecha_bautismo__year=anio,
        nuevo_creyente=False,
    )

    if mes:
        miembros = miembros.filter(fecha_bautismo__month=mes)

    if solo_activos:
        miembros = miembros.filter(activo=True)

    miembros = miembros.order_by("fecha_bautismo", "apellidos", "nombres")

    # Estadísticas por mes
    stats_mes = (
        Miembro.objects.filter(
            tenant=request.tenant,
            fecha_bautismo__isnull=False,
            fecha_bautismo__year=anio,
        )
        .annotate(mes_bautismo=ExtractMonth("fecha_bautismo"))
        .values("mes_bautismo")
        .annotate(total=Count("id"))
        .order_by("mes_bautismo")
    )

    # Convertir a dict para fácil acceso
    stats_dict = {s["mes_bautismo"]: s["total"] for s in stats_mes}

    # Lista de años disponibles
    anios_disponibles = (
        Miembro.objects.filter(
            tenant=request.tenant,
            fecha_bautismo__isnull=False,
        )
        .dates("fecha_bautismo", "year")
        .values_list("fecha_bautismo__year", flat=True)
        .distinct()
    )

    context = {
        "miembros": miembros,
        "anio": anio,
        "mes": mes,
        "nombre_mes": MESES_ES.get(mes, "") if mes else "",
        "solo_activos": solo_activos,
        "total": miembros.count(),
        "stats_dict": stats_dict,
        "MESES_ES": MESES_ES,
        "anios_disponibles": sorted(set(anios_disponibles), reverse=True),
        "CFG": CFG,
    }

    return render(request, "miembros_app/reportes/bautismos.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE: REINGRESOS / REINCORPORADOS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def reporte_reingresos(request):
    """
    Reporte de miembros reincorporados (etapa_actual = 'reincorporado').
    """
    CFG = ConfiguracionSistema.load(request.tenant)
    hoy = timezone.localdate()

    # Filtros de fecha
    anio_str = request.GET.get("anio", "").strip()
    anio = int(anio_str) if anio_str.isdigit() else None

    solo_activos = request.GET.get("solo_activos", "1") == "1"
    origen_filtro = request.GET.get("origen", "").strip()

    miembros = Miembro.objects.filter(
        tenant=request.tenant,
        etapa_actual="reincorporado",
    )

    if anio:
        miembros = miembros.filter(fecha_reingreso__year=anio)

    if solo_activos:
        miembros = miembros.filter(activo=True)

    if origen_filtro:
        miembros = miembros.filter(origen_reingreso=origen_filtro)

    miembros = miembros.order_by("-fecha_reingreso", "apellidos", "nombres")

    # Estadísticas por origen
    stats_origen = (
        Miembro.objects.filter(
            tenant=request.tenant,
            etapa_actual="reincorporado",
        )
        .exclude(origen_reingreso__isnull=True)
        .exclude(origen_reingreso="")
        .values("origen_reingreso")
        .annotate(total=Count("id"))
    )

    # Años disponibles
    anios_disponibles = (
        Miembro.objects.filter(
            tenant=request.tenant,
            etapa_actual="reincorporado",
            fecha_reingreso__isnull=False,
        )
        .dates("fecha_reingreso", "year")
        .values_list("fecha_reingreso__year", flat=True)
        .distinct()
    )

    ORIGEN_CHOICES = [
        ("descarriado", "Descarriado"),
        ("traslado", "Traslado"),
        ("pausa", "Pausa voluntaria"),
    ]

    context = {
        "miembros": miembros,
        "anio": anio,
        "solo_activos": solo_activos,
        "origen_filtro": origen_filtro,
        "total": miembros.count(),
        "stats_origen": stats_origen,
        "ORIGEN_CHOICES": ORIGEN_CHOICES,
        "anios_disponibles": sorted(set(anios_disponibles), reverse=True) if anios_disponibles else [],
        "CFG": CFG,
    }

    return render(request, "miembros_app/reportes/reingresos.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE: MINISTERIALES (OBREROS, PASTORES, EVANGELISTAS)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def reporte_ministeriales(request):
    """
    Reporte de miembros con rol ministerial (pastores, evangelistas, misioneros, obreros).
    """
    CFG = ConfiguracionSistema.load(request.tenant)

    rol_filtro = request.GET.get("rol", "").strip()
    estado_filtro = request.GET.get("estado_ministerial", "").strip()
    solo_activos = request.GET.get("solo_activos", "1") == "1"

    miembros = Miembro.objects.filter(
        tenant=request.tenant,
        nuevo_creyente=False,
    ).exclude(
        rol_ministerial=""
    ).exclude(
        rol_ministerial__isnull=True
    )

    if rol_filtro:
        miembros = miembros.filter(rol_ministerial=rol_filtro)

    if estado_filtro:
        miembros = miembros.filter(estado_ministerial=estado_filtro)

    if solo_activos:
        miembros = miembros.filter(activo=True)

    miembros = miembros.order_by("rol_ministerial", "apellidos", "nombres")

    # Estadísticas por rol
    stats_rol = (
        Miembro.objects.filter(tenant=request.tenant)
        .exclude(rol_ministerial="")
        .exclude(rol_ministerial__isnull=True)
        .values("rol_ministerial")
        .annotate(total=Count("id"))
        .order_by("rol_ministerial")
    )

    ROL_CHOICES = [
        ("pastor", "Pastor"),
        ("evangelista", "Evangelista"),
        ("misionero", "Misionero"),
        ("obrero", "Obrero"),
        ("diacono", "Diácono"),
        ("lider", "Líder"),
    ]

    ESTADO_MINISTERIAL_CHOICES = [
        ("activo", "Activo"),
        ("pausa", "En pausa"),
        ("retirado", "Retirado"),
    ]

    context = {
        "miembros": miembros,
        "rol_filtro": rol_filtro,
        "estado_filtro": estado_filtro,
        "solo_activos": solo_activos,
        "total": miembros.count(),
        "stats_rol": stats_rol,
        "ROL_CHOICES": ROL_CHOICES,
        "ESTADO_MINISTERIAL_CHOICES": ESTADO_MINISTERIAL_CHOICES,
        "CFG": CFG,
    }

    return render(request, "miembros_app/reportes/ministeriales.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE: ATENCIÓN PASTORAL (VULNERABLES, DISCIPLINA, OBSERVACIÓN)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def reporte_atencion_pastoral(request):
    """
    Reporte de miembros que requieren atención pastoral especial:
    - Situación económica vulnerable/crítica
    - En disciplina
    - En observación
    - Descarriados (aún activos o recientes)
    """
    CFG = ConfiguracionSistema.load(request.tenant)

    tipo_filtro = request.GET.get("tipo", "").strip()

    # Base: miembros del tenant
    miembros_base = Miembro.objects.filter(
        tenant=request.tenant,
        nuevo_creyente=False,
    )

    if tipo_filtro == "vulnerable":
        miembros = miembros_base.filter(
            situacion_economica__in=["vulnerable", "critica"],
            activo=True,
        )
        titulo_seccion = "Situación Económica Vulnerable/Crítica"
    elif tipo_filtro == "disciplina":
        miembros = miembros_base.filter(
            estado_miembro="disciplina",
        )
        titulo_seccion = "En Disciplina"
    elif tipo_filtro == "observacion":
        miembros = miembros_base.filter(
            estado_miembro="observacion",
        )
        titulo_seccion = "En Observación"
    elif tipo_filtro == "descarriado":
        miembros = miembros_base.filter(
            estado_miembro="descarriado",
        )
        titulo_seccion = "Descarriados"
    elif tipo_filtro == "pasivo":
        miembros = miembros_base.filter(
            estado_miembro="pasivo",
            activo=True,
        )
        titulo_seccion = "Miembros Pasivos"
    else:
        # Sin filtro: mostrar todos los que requieren atención
        miembros = miembros_base.filter(
            Q(situacion_economica__in=["vulnerable", "critica"]) |
            Q(estado_miembro__in=["disciplina", "observacion", "descarriado", "pasivo"])
        )
        titulo_seccion = "Todos los casos"

    miembros = miembros.order_by("estado_miembro", "apellidos", "nombres")

    # Contadores por tipo
    contadores = {
        "vulnerable": miembros_base.filter(
            situacion_economica__in=["vulnerable", "critica"], activo=True
        ).count(),
        "disciplina": miembros_base.filter(estado_miembro="disciplina").count(),
        "observacion": miembros_base.filter(estado_miembro="observacion").count(),
        "descarriado": miembros_base.filter(estado_miembro="descarriado").count(),
        "pasivo": miembros_base.filter(estado_miembro="pasivo", activo=True).count(),
    }

    TIPO_CHOICES = [
        ("", "Todos"),
        ("vulnerable", "Vulnerables/Críticos"),
        ("disciplina", "En Disciplina"),
        ("observacion", "En Observación"),
        ("descarriado", "Descarriados"),
        ("pasivo", "Pasivos"),
    ]

    context = {
        "miembros": miembros,
        "tipo_filtro": tipo_filtro,
        "titulo_seccion": titulo_seccion,
        "total": miembros.count(),
        "contadores": contadores,
        "TIPO_CHOICES": TIPO_CHOICES,
        "CFG": CFG,
    }

    return render(request, "miembros_app/reportes/atencion_pastoral.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE: FAMILIAS / HOGARES
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def reporte_familias(request):
    """
    Reporte de familias/hogares con sus miembros.
    """
    CFG = ConfiguracionSistema.load(request.tenant)

    solo_completas = request.GET.get("solo_completas", "0") == "1"

    hogares = HogarFamiliar.objects.filter(
        tenant=request.tenant,
    ).prefetch_related(
        "miembros__miembro"
    ).order_by("nombre")

    if solo_completas:
        # Hogares con más de 1 miembro
        hogares = hogares.annotate(
            num_miembros=Count("miembros")
        ).filter(num_miembros__gt=1)

    # Preparar datos de hogares
    hogares_data = []
    for hogar in hogares:
        miembros_hogar = hogar.miembros.select_related("miembro").order_by("-es_principal", "rol")
        hogares_data.append({
            "hogar": hogar,
            "miembros": miembros_hogar,
            "total_miembros": miembros_hogar.count(),
        })

    # Estadísticas
    total_hogares = hogares.count()
    total_miembros_en_hogares = HogarMiembro.objects.filter(
        hogar__tenant=request.tenant
    ).values("miembro").distinct().count()

    context = {
        "hogares_data": hogares_data,
        "solo_completas": solo_completas,
        "total_hogares": total_hogares,
        "total_miembros_en_hogares": total_miembros_en_hogares,
        "CFG": CFG,
    }

    return render(request, "miembros_app/reportes/familias.html", context)