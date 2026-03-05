

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET
from django.db.models import Sum, Q
from django.core.exceptions import PermissionDenied
from decimal import Decimal
import json
import datetime

from ..models import (
    MovimientoFinanciero,
    CuentaFinanciera,
)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def egreso_recibo(request, pk):
    """
    Vista SOLO para imprimir el recibo de un EGRESO (formato 80mm).
    """
    egreso = get_object_or_404(
        MovimientoFinanciero,
        pk=pk,
        tipo="egreso",
        tenant=request.tenant  # 👈 FILTRAR POR TENANT
    )

    context = {
        "egreso": egreso,
        "auto_print": True,
    }
    return render(
        request,
        "finanzas_app/recibos/egreso_recibo.html",
        context
    )


@login_required
def dashboard(request):
    u = request.user
    tenant = request.tenant  # 👈 TENANT

    # Si NO tiene permiso de ver dashboard, lo mandamos a una pantalla permitida
    if not (u.is_superuser or u.has_perm("finanzas_app.ver_dashboard_finanzas")):
        if u.has_perm("finanzas_app.view_movimientofinanciero"):
            return redirect("finanzas_app:movimientos_listado")

        if u.has_perm("finanzas_app.view_cuentaporpagar"):
            return redirect("finanzas_app:cxp_list")

        if u.has_perm("finanzas_app.view_proveedorfinanciero"):
            return redirect("finanzas_app:proveedores_list")

        if u.has_perm("finanzas_app.view_cuentafinanciera"):
            return redirect("finanzas_app:cuentas_listado")

        if u.has_perm("finanzas_app.view_categoriamovimiento"):
            return redirect("finanzas_app:categorias_listado")

        raise PermissionDenied("No tienes permisos para acceder al módulo de Finanzas.")

    from django.db.models.functions import TruncMonth
    from dateutil.relativedelta import relativedelta

    hoy = datetime.date.today()

    # ---- TOTALES DEL MES ACTUAL ----
    movimientos_mes = MovimientoFinanciero.objects.filter(
        tenant=tenant,  # 👈 FILTRAR POR TENANT
        fecha__year=hoy.year,
        fecha__month=hoy.month
    ).exclude(estado="anulado")

    totales_mes = movimientos_mes.aggregate(
        ingresos=Sum("monto", filter=Q(tipo="ingreso")),
        egresos=Sum("monto", filter=Q(tipo="egreso")),
    )

    ingresos_mes = totales_mes.get("ingresos") or Decimal("0")
    egresos_mes = totales_mes.get("egresos") or Decimal("0")
    balance_mes = ingresos_mes - egresos_mes

    # ---- TOTALES GENERALES (histórico) ----
    totales_historico = MovimientoFinanciero.objects.filter(
        tenant=tenant  # 👈 FILTRAR POR TENANT
    ).exclude(
        estado="anulado"
    ).aggregate(
        ingresos=Sum("monto", filter=Q(tipo="ingreso")),
        egresos=Sum("monto", filter=Q(tipo="egreso")),
    )

    ingresos_total = totales_historico.get("ingresos") or Decimal("0")
    egresos_total = totales_historico.get("egresos") or Decimal("0")
    balance_total = ingresos_total - egresos_total

    # ---- SALDO TOTAL EN CUENTAS ----
    saldo_inicial_cuentas = CuentaFinanciera.objects.filter(
        tenant=tenant,  # 👈 FILTRAR POR TENANT
        esta_activa=True
    ).aggregate(total=Sum("saldo_inicial"))["total"] or Decimal("0")

    saldo_actual = saldo_inicial_cuentas + balance_total

    # ---- ÚLTIMOS MOVIMIENTOS ----
    ultimos_movimientos = MovimientoFinanciero.objects.filter(
        tenant=tenant  # 👈 FILTRAR POR TENANT
    ).select_related(
        "cuenta", "categoria"
    ).exclude(estado="anulado").order_by("-fecha", "-creado_en")[:10]

    # ---- DATOS PARA GRÁFICO DE BARRAS (últimos 6 meses) ----
    meses_atras = 6
    fecha_inicio_grafico = (hoy - relativedelta(months=meses_atras-1)).replace(day=1)

    datos_mensuales = MovimientoFinanciero.objects.filter(
        tenant=tenant,  # 👈 FILTRAR POR TENANT
        fecha__gte=fecha_inicio_grafico
    ).exclude(estado="anulado").annotate(
        mes=TruncMonth("fecha")
    ).values("mes", "tipo").annotate(
        total=Sum("monto")
    ).order_by("mes")

    # Preparar estructura para el gráfico
    meses_labels = []
    ingresos_por_mes = []
    egresos_por_mes = []

    NOMBRES_MESES = [
        "", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
        "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
    ]

    for i in range(meses_atras):
        fecha_mes = (hoy - relativedelta(months=meses_atras-1-i)).replace(day=1)
        meses_labels.append(f"{NOMBRES_MESES[fecha_mes.month]} {fecha_mes.year}")

        ingreso_mes_i = Decimal("0")
        egreso_mes_i = Decimal("0")

        for dato in datos_mensuales:
            if dato["mes"].year == fecha_mes.year and dato["mes"].month == fecha_mes.month:
                if dato["tipo"] == "ingreso":
                    ingreso_mes_i = dato["total"]
                else:
                    egreso_mes_i = dato["total"]

        ingresos_por_mes.append(float(ingreso_mes_i))
        egresos_por_mes.append(float(egreso_mes_i))

    # ---- DATOS PARA GRÁFICO DE DONA (distribución por categoría - mes actual) ----
    distribucion_ingresos = MovimientoFinanciero.objects.filter(
        tenant=tenant,  # 👈 FILTRAR POR TENANT
        tipo="ingreso",
        fecha__year=hoy.year,
        fecha__month=hoy.month
    ).exclude(estado="anulado").values(
        "categoria__nombre"
    ).annotate(
        total=Sum("monto")
    ).order_by("-total")[:6]

    categorias_labels = [d["categoria__nombre"] for d in distribucion_ingresos]
    categorias_valores = [float(d["total"]) for d in distribucion_ingresos]

    # Si no hay datos, poner placeholder
    if not categorias_labels:
        categorias_labels = ["Sin datos"]
        categorias_valores = [0]

    # ---- RESUMEN POR CUENTA ----
    cuentas_resumen = []
    for cuenta in CuentaFinanciera.objects.filter(tenant=tenant, esta_activa=True):  # 👈 FILTRAR POR TENANT
        movs_cuenta = MovimientoFinanciero.objects.filter(
            tenant=tenant,  # 👈 FILTRAR POR TENANT
            cuenta=cuenta
        ).exclude(estado="anulado").aggregate(
            ingresos=Sum("monto", filter=Q(tipo="ingreso")),
            egresos=Sum("monto", filter=Q(tipo="egreso")),
        )

        ing = movs_cuenta.get("ingresos") or Decimal("0")
        egr = movs_cuenta.get("egresos") or Decimal("0")
        saldo = cuenta.saldo_inicial + ing - egr

        cuentas_resumen.append({
            "cuenta": cuenta,
            "saldo_actual": saldo,
            "ingresos": ing,
            "egresos": egr,
        })

    # ---- ESTADÍSTICAS RÁPIDAS ----
    total_movimientos_mes = movimientos_mes.count()
    count_ingresos = movimientos_mes.filter(tipo="ingreso").count()
    promedio_ingreso = ingresos_mes / max(count_ingresos, 1)

    # ---- TOP CATEGORÍAS DEL MES ----
    top_categorias_ingreso = MovimientoFinanciero.objects.filter(
        tenant=tenant,  # 👈 FILTRAR POR TENANT
        tipo="ingreso",
        fecha__year=hoy.year,
        fecha__month=hoy.month
    ).exclude(estado="anulado").values(
        "categoria__nombre"
    ).annotate(
        total=Sum("monto")
    ).order_by("-total")[:5]

    top_categorias_egreso = MovimientoFinanciero.objects.filter(
        tenant=tenant,  # 👈 FILTRAR POR TENANT
        tipo="egreso",
        fecha__year=hoy.year,
        fecha__month=hoy.month
    ).exclude(estado="anulado").values(
        "categoria__nombre"
    ).annotate(
        total=Sum("monto")
    ).order_by("-total")[:5]

    context = {
        # Resumen del mes
        "resumen": {
            "ingresos_mes": ingresos_mes,
            "egresos_mes": egresos_mes,
            "balance": balance_mes,
        },
        # Totales históricos
        "historico": {
            "ingresos_total": ingresos_total,
            "egresos_total": egresos_total,
            "balance_total": balance_total,
        },
        # Saldo actual
        "saldo_actual": saldo_actual,
        # Últimos movimientos
        "ultimos_movimientos": ultimos_movimientos,
        # Datos para gráfico de barras (JSON)
        "grafico_barras": json.dumps({
            "labels": meses_labels,
            "ingresos": ingresos_por_mes,
            "egresos": egresos_por_mes,
        }),
        # Datos para gráfico de dona (JSON)
        "grafico_dona": json.dumps({
            "labels": categorias_labels,
            "valores": categorias_valores,
        }),
        # Resumen por cuenta
        "cuentas_resumen": cuentas_resumen,
        # Top categorías
        "top_categorias_ingreso": top_categorias_ingreso,
        "top_categorias_egreso": top_categorias_egreso,
        # Estadísticas
        "stats": {
            "total_movimientos_mes": total_movimientos_mes,
            "promedio_ingreso": promedio_ingreso,
        },
        # Info de fecha
        "mes_actual": hoy.strftime("%B %Y").capitalize(),
        "fecha_hoy": hoy,
    }
    return render(request, "finanzas_app/dashboard.html", context)