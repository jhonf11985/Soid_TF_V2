from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum
from django.shortcuts import render
from django.utils import timezone
from miembros_app.views.utils import calcular_edad, porcentaje
from core.utils_config import get_edad_minima_miembro_oficial

from miembros_app.models import Miembro
from finanzas_app.models import (
    MovimientoFinanciero,
    CuentaFinanciera,
    CuentaPorPagar,
)


def _cutoff_nacimiento_por_edad(edad_minima: int, hoy: date) -> date:
    try:
        return hoy.replace(year=hoy.year - edad_minima)
    except ValueError:
        return hoy.replace(month=2, day=28, year=hoy.year - edad_minima)


def _diagnostico_membresia(activos, pasivos, observacion, disciplina, catecumenos, descarriados, total):
    """
    Diagnóstico pastoral basado en la condición real de la membresía.
    """
    if total == 0:
        return {
            "nivel": "sin_datos",
            "titulo": "Sin base de evaluación",
            "mensaje": "Aún no hay miembros oficiales suficientes para evaluar la condición de la iglesia.",
        }

    if activos >= (total * 0.75):
        return {
            "nivel": "saludable",
            "titulo": "Iglesia firme",
            "mensaje": "La congregación se mantiene estable. La mayoría camina activamente en la vida de la iglesia.",
        }

    if catecumenos >= (total * 0.35):
        return {
            "nivel": "crecimiento",
            "titulo": "Tiempo de formación",
            "mensaje": "Dios está añadiendo personas. Muchos están en proceso y necesitan acompañamiento cercano.",
        }

    if disciplina >= (total * 0.20) or observacion >= (total * 0.25):
        return {
            "nivel": "orden",
            "titulo": "Tiempo de corrección",
            "mensaje": "La iglesia atraviesa un proceso de orden. Algunos hermanos requieren cuidado pastoral cercano.",
        }

    if pasivos + descarriados > activos:
        return {
            "nivel": "enfriamiento",
            "titulo": "La iglesia necesita cercanía",
            "mensaje": "Hay más hermanos detenidos que caminando. Conviene acercarse, escuchar y pastorear.",
        }

    if activos <= (total * 0.40):
        return {
            "nivel": "riesgo",
            "titulo": "Necesita atención pastoral",
            "mensaje": "La membresía activa es baja. Es momento de fortalecer, visitar y recuperar.",
        }

    return {
        "nivel": "atencion",
        "titulo": "Momento de cuidado",
        "mensaje": "La iglesia se mantiene, pero algunos hermanos necesitan ser acompañados más de cerca.",
    }


def _diagnostico_finanzas(ingresos_mes, egresos_mes, saldo_total, cxp_vencidas, variacion_ingresos):
    """
    Diagnóstico financiero pastoral.
    No es contable, es estratégico para el pastor.
    """
    balance_mes = ingresos_mes - egresos_mes

    # Sin movimientos
    if ingresos_mes == 0 and egresos_mes == 0:
        return {
            "nivel": "sin_datos",
            "titulo": "Sin movimientos",
            "mensaje": "No hay movimientos registrados este mes.",
        }

    # Cuentas vencidas (alerta máxima)
    if cxp_vencidas > 0:
        return {
            "nivel": "critico",
            "titulo": "Pagos vencidos",
            "mensaje": f"Hay {cxp_vencidas} compromiso(s) vencido(s) que requieren atención inmediata.",
        }

    # Balance negativo fuerte
    if balance_mes < 0 and abs(balance_mes) > (ingresos_mes * Decimal("0.3")):
        return {
            "nivel": "riesgo",
            "titulo": "Egresos elevados",
            "mensaje": "Los egresos superan significativamente los ingresos. Conviene revisar compromisos.",
        }

    # Balance negativo leve
    if balance_mes < 0:
        return {
            "nivel": "atencion",
            "titulo": "Mes ajustado",
            "mensaje": "Los egresos superaron los ingresos este mes. El saldo general aún sostiene.",
        }

    # Ingresos bajaron mucho vs mes anterior
    if variacion_ingresos is not None and variacion_ingresos < Decimal("-0.20"):
        return {
            "nivel": "atencion",
            "titulo": "Ingresos en baja",
            "mensaje": "Los ingresos bajaron más del 20% respecto al mes anterior.",
        }

    # Todo bien
    if balance_mes > 0 and saldo_total > 0:
        return {
            "nivel": "saludable",
            "titulo": "Finanzas estables",
            "mensaje": "Los ingresos cubren los egresos. La iglesia se sostiene bien este mes.",
        }

    return {
        "nivel": "atencion",
        "titulo": "Revisar finanzas",
        "mensaje": "Conviene dar seguimiento a los movimientos del mes.",
    }


def _obtener_rango_mes(año, mes):
    """Retorna (primer_dia, ultimo_dia) de un mes dado."""
    primer_dia = date(año, mes, 1)
    if mes == 12:
        ultimo_dia = date(año + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(año, mes + 1, 1) - timedelta(days=1)
    return primer_dia, ultimo_dia


def _obtener_finanzas_ejecutivo(total_oficiales=0):
    """
    Calcula los KPIs financieros para el Centro Ejecutivo.
    Retorna dict con toda la info necesaria.
    """
    from finanzas_app.models import CategoriaMovimiento
    
    hoy = date.today()
    primer_dia_mes = hoy.replace(day=1)
    
    # Mes anterior
    if hoy.month == 1:
        primer_dia_mes_anterior = hoy.replace(year=hoy.year - 1, month=12, day=1)
        ultimo_dia_mes_anterior = hoy.replace(day=1) - timedelta(days=1)
    else:
        primer_dia_mes_anterior = hoy.replace(month=hoy.month - 1, day=1)
        ultimo_dia_mes_anterior = hoy.replace(day=1) - timedelta(days=1)

    # ============================================================
    # 1) SALDOS POR TIPO DE CUENTA
    # ============================================================
    cuentas_activas = CuentaFinanciera.objects.filter(esta_activa=True)
    
    saldo_total = Decimal("0")
    saldo_banco = Decimal("0")
    saldo_caja = Decimal("0")
    
    for cuenta in cuentas_activas:
        saldo_inicial = cuenta.saldo_inicial or Decimal("0")
        
        ingresos_cuenta = MovimientoFinanciero.objects.filter(
            cuenta=cuenta,
            tipo="ingreso",
            estado__in=["confirmado", "cuadrado"]
        ).aggregate(total=Sum("monto"))["total"] or Decimal("0")
        
        egresos_cuenta = MovimientoFinanciero.objects.filter(
            cuenta=cuenta,
            tipo="egreso",
            estado__in=["confirmado", "cuadrado"]
        ).aggregate(total=Sum("monto"))["total"] or Decimal("0")
        
        saldo_cuenta = saldo_inicial + ingresos_cuenta - egresos_cuenta
        saldo_total += saldo_cuenta
        
        if cuenta.tipo == "banco":
            saldo_banco += saldo_cuenta
        elif cuenta.tipo == "caja":
            saldo_caja += saldo_cuenta

    # ============================================================
    # 2) INGRESOS Y EGRESOS DEL MES
    # ============================================================
    movimientos_mes = MovimientoFinanciero.objects.filter(
        fecha__gte=primer_dia_mes,
        fecha__lte=hoy,
        estado__in=["confirmado", "cuadrado"]
    )

    ingresos_mes = movimientos_mes.filter(tipo="ingreso").aggregate(
        total=Sum("monto")
    )["total"] or Decimal("0")

    egresos_mes = movimientos_mes.filter(tipo="egreso").aggregate(
        total=Sum("monto")
    )["total"] or Decimal("0")

    balance_mes = ingresos_mes - egresos_mes

    # ============================================================
    # 3) INGRESOS MES ANTERIOR (para comparar)
    # ============================================================
    ingresos_mes_anterior = MovimientoFinanciero.objects.filter(
        fecha__gte=primer_dia_mes_anterior,
        fecha__lte=ultimo_dia_mes_anterior,
        tipo="ingreso",
        estado__in=["confirmado", "cuadrado"]
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0")

    # Variación porcentual
    if ingresos_mes_anterior > 0:
        variacion_ingresos = ((ingresos_mes - ingresos_mes_anterior) / ingresos_mes_anterior)
    else:
        variacion_ingresos = None

    # ============================================================
    # 4) CUENTAS POR PAGAR
    # ============================================================
    cxp_pendientes = CuentaPorPagar.objects.filter(
        estado__in=["pendiente", "parcial", "vencida"]
    )
    
    cxp_vencidas = cxp_pendientes.filter(
        Q(estado="vencida") | Q(fecha_vencimiento__lt=hoy)
    ).count()

    cxp_proximas_7_dias = cxp_pendientes.filter(
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=7)
    ).count()

    total_por_pagar = cxp_pendientes.aggregate(
        total=Sum("monto_total") - Sum("monto_pagado")
    )
    monto_por_pagar = (total_por_pagar.get("total") or Decimal("0"))
    
    # Recalcular correctamente
    monto_por_pagar = sum(
        (cxp.monto_total - cxp.monto_pagado) for cxp in cxp_pendientes
    )

    # ============================================================
    # 5) DIEZMOS DEL MES
    # ============================================================
    # Buscar categorías de diezmo (por código o nombre)
    categorias_diezmo = CategoriaMovimiento.objects.filter(
        Q(codigo__icontains="diezmo") | Q(nombre__icontains="diezmo"),
        tipo="ingreso",
        activo=True
    )

    movimientos_diezmo_mes = MovimientoFinanciero.objects.filter(
        fecha__gte=primer_dia_mes,
        fecha__lte=hoy,
        tipo="ingreso",
        categoria__in=categorias_diezmo,
        estado__in=["confirmado", "cuadrado"]
    )

    total_diezmos_mes = movimientos_diezmo_mes.aggregate(
        total=Sum("monto")
    )["total"] or Decimal("0")

    # Personas que diezmaron (únicas)
    personas_diezmaron = movimientos_diezmo_mes.filter(
        persona_asociada__isnull=False
    ).values("persona_asociada").distinct().count()

    # Calcular ratio de diezmadores vs oficiales
    if total_oficiales > 0:
        ratio_diezmadores = personas_diezmaron / total_oficiales
    else:
        ratio_diezmadores = 0

    # ============================================================
    # 6) TENDENCIA DE INGRESOS (últimos 4 meses)
    # ============================================================
    tendencia = []
    meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", 
                     "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    for i in range(3, -1, -1):  # 3, 2, 1, 0 (hace 3 meses hasta actual)
        # Calcular año y mes
        mes_calc = hoy.month - i
        año_calc = hoy.year
        
        while mes_calc <= 0:
            mes_calc += 12
            año_calc -= 1
        
        primer_dia, ultimo_dia = _obtener_rango_mes(año_calc, mes_calc)
        
        ingresos_periodo = MovimientoFinanciero.objects.filter(
            fecha__gte=primer_dia,
            fecha__lte=ultimo_dia,
            tipo="ingreso",
            estado__in=["confirmado", "cuadrado"]
        ).aggregate(total=Sum("monto"))["total"] or Decimal("0")
        
        tendencia.append({
            "mes": meses_nombres[mes_calc - 1],
            "valor": float(ingresos_periodo),
            "es_actual": (i == 0)
        })

    # Calcular máximo para escala del gráfico
    max_tendencia = max((t["valor"] for t in tendencia), default=1)

    # ============================================================
    # 7) DIAGNÓSTICO
    # ============================================================
    diag = _diagnostico_finanzas(
        ingresos_mes,
        egresos_mes,
        saldo_total,
        cxp_vencidas,
        variacion_ingresos
    )

    # ============================================================
    # 8) FOCOS FINANCIEROS
    # ============================================================
    focos = []

    if cxp_vencidas > 0:
        focos.append({
            "nivel": "alta",
            "titulo": "Pagos vencidos",
            "detalle": f"{cxp_vencidas} compromiso(s) pasaron su fecha de vencimiento.",
            "cta_texto": "Ver CxP",
            "cta_url": "/finanzas/cuentas-por-pagar/?estado=vencida",
        })

    if cxp_proximas_7_dias > 0:
        focos.append({
            "nivel": "media",
            "titulo": "Pagos próximos",
            "detalle": f"{cxp_proximas_7_dias} compromiso(s) vencen en los próximos 7 días.",
            "cta_texto": "Ver CxP",
            "cta_url": "/finanzas/cuentas-por-pagar/",
        })

    if variacion_ingresos is not None and variacion_ingresos < Decimal("-0.20"):
        porcentaje_baja = abs(variacion_ingresos) * 100
        focos.append({
            "nivel": "media",
            "titulo": "Ingresos en baja",
            "detalle": f"Los ingresos bajaron {porcentaje_baja:.0f}% respecto al mes anterior.",
            "cta_texto": "Ver movimientos",
            "cta_url": "/finanzas/movimientos/",
        })

    return {
        "saldo_total": saldo_total,
        "saldo_banco": saldo_banco,
        "saldo_caja": saldo_caja,
        "ingresos_mes": ingresos_mes,
        "egresos_mes": egresos_mes,
        "balance_mes": balance_mes,
        "variacion_ingresos": variacion_ingresos,
        "cxp_vencidas": cxp_vencidas,
        "cxp_proximas": cxp_proximas_7_dias,
        "monto_por_pagar": monto_por_pagar,
        "diag": diag,
        "focos": focos,
        # Diezmos
        "diezmos": {
            "total": total_diezmos_mes,
            "personas": personas_diezmaron,
            "total_oficiales": total_oficiales,
            "ratio": ratio_diezmadores,
        },
        # Tendencia
        "tendencia": tendencia,
        "tendencia_max": max_tendencia,
    }


@login_required
def inicio(request):
    """
    Centro Ejecutivo · Inicio (Nivel 1)
    - KPIs de miembros
    - KPIs de finanzas
    - Diagnósticos
    - Focos principales (unificados)
    """
    miembros = Miembro.objects.filter(activo=True)
    edad_minima = get_edad_minima_miembro_oficial()
    hoy = date.today()

    # ============================================================
    # 1) CONTEO DE MEMBRESÍA OFICIAL
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

    miembros_descarriados = Miembro.objects.filter(activo=False, razon_salida__isnull=False)
    descarriados = sum(
        1 for m in miembros_descarriados
        if calcular_edad(m.fecha_nacimiento) is not None
        and calcular_edad(m.fecha_nacimiento) >= edad_minima
        and "descarri" in str(m.razon_salida).lower()
    )

    total_oficiales = activos + pasivos + observacion + disciplina + catecumenos
    total_base = total_oficiales

    # ============================================================
    # 2) DIAGNÓSTICO MEMBRESÍA
    # ============================================================
    ratio_activos = (activos / total_oficiales) if total_oficiales else 0.0

    diag_membresia = _diagnostico_membresia(
        activos, pasivos, observacion, disciplina,
        catecumenos, descarriados, total_oficiales
    )

    desglose_no_activos = []
    if catecumenos:
        desglose_no_activos.append({"label": "Catecúmenos", "value": catecumenos})
    if pasivos:
        desglose_no_activos.append({"label": "Pasivos", "value": pasivos})
    if observacion:
        desglose_no_activos.append({"label": "Observación", "value": observacion})
    if disciplina:
        desglose_no_activos.append({"label": "Disciplina", "value": disciplina})

    # ============================================================
    # 3) KPIs MEMBRESÍA
    # ============================================================
    total_miembros_registrados = miembros.count()

    hace_7_dias = timezone.now() - timedelta(days=7)
    nuevos_creyentes_semana = Miembro.objects.filter(
        nuevo_creyente=True, activo=True, fecha_creacion__gte=hace_7_dias
    ).count()

    # ============================================================
    # 4) FINANZAS
    # ============================================================
    finanzas = _obtener_finanzas_ejecutivo(total_oficiales=total_oficiales)

    # ============================================================
    # 5) FOCOS PRINCIPALES (unificados: membresía + finanzas)
    # ============================================================
    focos = []

    # Focos de finanzas primero (dinero es urgente)
    focos.extend(finanzas["focos"])

    # Focos de membresía
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

    oficiales_no_activos = total_oficiales - activos
    if total_oficiales and oficiales_no_activos:
        focos.append({
            "nivel": "media" if ratio_activos >= 0.70 else "alta",
            "titulo": "Miembros oficiales fuera de activo",
            "detalle": f"{oficiales_no_activos} oficiales no están en estado pastoral activo.",
            "cta_texto": "Revisar",
            "cta_url": "/ejecutivo/personas/?filtro=oficiales_no_activos",
        })

    # Ordenar focos por nivel (alta primero)
    orden_nivel = {"alta": 0, "media": 1, "baja": 2}
    focos.sort(key=lambda x: orden_nivel.get(x["nivel"], 99))

    # Mensaje general
    focos_altos = sum(1 for f in focos if f["nivel"] == "alta")
    if not focos:
        estado_general = "Todo se ve estable. No hay focos críticos ahora mismo."
    elif focos_altos > 0:
        estado_general = f"Hay {focos_altos} foco(s) urgente(s) que requieren atención."
    else:
        estado_general = f"Hay {len(focos)} foco(s) que merecen seguimiento."

    context = {
        "estado_general": estado_general,

        # KPIs membresía
        "kpis": [
            {"label": "Miembros registrados", "value": total_miembros_registrados, "sub": "Incluye niños y nuevos creyentes"},
            {"label": "Miembros oficiales", "value": total_oficiales, "sub": f"Mayores de {edad_minima} años"},
            {"label": "Nuevos creyentes", "value": nuevos_creyentes_semana, "sub": "Últimos 7 días"},
            {"label": "Descarriados", "value": descarriados, "sub": "Necesitan seguimiento"},
        ],

        # Membresía (tarjeta diagnóstico)
        "membresia": {
            "oficiales_total": total_oficiales,
            "oficiales_estado_activo": activos,
            "ratio": ratio_activos,
            "diag": diag_membresia,
            "desglose_no_activos": desglose_no_activos,
            "cta_url": "/ejecutivo/personas/?filtro=oficiales_no_activos",
        },

        # Estados membresía
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

        # FINANZAS (nuevo)
        "finanzas": {
            "saldo_total": finanzas["saldo_total"],
            "saldo_banco": finanzas["saldo_banco"],
            "saldo_caja": finanzas["saldo_caja"],
            "ingresos_mes": finanzas["ingresos_mes"],
            "egresos_mes": finanzas["egresos_mes"],
            "balance_mes": finanzas["balance_mes"],
            "variacion_ingresos": finanzas["variacion_ingresos"],
            "cxp_vencidas": finanzas["cxp_vencidas"],
            "cxp_proximas": finanzas["cxp_proximas"],
            "monto_por_pagar": finanzas["monto_por_pagar"],
            "diag": finanzas["diag"],
            "cta_url": "/finanzas/",
            # Diezmos
            "diezmos": finanzas["diezmos"],
            # Tendencia
            "tendencia": finanzas["tendencia"],
            "tendencia_max": finanzas["tendencia_max"],
        },

        # Focos unificados (máximo 5)
        "focos": focos[:5],
    }

    return render(request, "ejecutivo_app/inicio.html", context)


@login_required
def personas(request):
    return render(request, "ejecutivo_app/personas.html", {})