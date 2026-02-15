# finanzas_app/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from decimal import Decimal
import json
import datetime
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from core.utils_config import get_config
from .models import MovimientoFinanciero
from collections import defaultdict
from .models import (
    MovimientoFinanciero,
    CuentaFinanciera,
    CategoriaMovimiento,
    ProveedorFinanciero,
    CuentaPorPagar,
)
from django.db.models import Count

from .forms import (
    MovimientoFinancieroForm,
    MovimientoIngresoForm,
    CuentaFinancieraForm,
    MovimientoEgresoForm,
    CategoriaMovimientoForm,
    ProveedorFinancieroForm,
    CuentaPorPagarForm,
)
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.core.exceptions import PermissionDenied





# ============================================
# DASHBOARD
# ============================================

@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def egreso_recibo(request, pk):
    ...

    """
    Vista SOLO para imprimir el recibo de un EGRESO (formato 80mm).
    """
    egreso = get_object_or_404(
        MovimientoFinanciero,
        pk=pk,
        tipo="egreso"
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

    # Si NO tiene permiso de ver dashboard, lo mandamos a una pantalla permitida
    if not (u.is_superuser or u.has_perm("finanzas_app.ver_dashboard_finanzas")):
        # Orden de entradas "naturales" del módulo
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

        # Si no tiene nada del módulo
        raise PermissionDenied("No tienes permisos para acceder al módulo de Finanzas.")

    
    from django.db.models.functions import TruncMonth
    from dateutil.relativedelta import relativedelta
    
    hoy = datetime.date.today()
    
    # ---- TOTALES DEL MES ACTUAL ----
    movimientos_mes = MovimientoFinanciero.objects.filter(
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
    totales_historico = MovimientoFinanciero.objects.exclude(
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
        esta_activa=True
    ).aggregate(total=Sum("saldo_inicial"))["total"] or Decimal("0")
    
    saldo_actual = saldo_inicial_cuentas + balance_total
    
    # ---- ÚLTIMOS MOVIMIENTOS ----
    ultimos_movimientos = MovimientoFinanciero.objects.select_related(
        "cuenta", "categoria"
    ).exclude(estado="anulado").order_by("-fecha", "-creado_en")[:10]
    
    # ---- DATOS PARA GRÁFICO DE BARRAS (últimos 6 meses) ----
    meses_atras = 6
    fecha_inicio_grafico = (hoy - relativedelta(months=meses_atras-1)).replace(day=1)
    
    datos_mensuales = MovimientoFinanciero.objects.filter(
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
    for cuenta in CuentaFinanciera.objects.filter(esta_activa=True):
        movs_cuenta = MovimientoFinanciero.objects.filter(
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
        tipo="ingreso",
        fecha__year=hoy.year,
        fecha__month=hoy.month
    ).exclude(estado="anulado").values(
        "categoria__nombre"
    ).annotate(
        total=Sum("monto")
    ).order_by("-total")[:5]
    
    top_categorias_egreso = MovimientoFinanciero.objects.filter(
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


# ============================================
# CUENTAS FINANCIERAS - CRUD
# ============================================

@login_required
@require_GET
@permission_required("finanzas_app.view_cuentafinanciera", raise_exception=True)
def cuentas_listado(request):
    ...

    """
    Listado de todas las cuentas financieras con saldo actual calculado.
    """
    cuentas = CuentaFinanciera.objects.all().order_by("-esta_activa", "nombre")
    
    total_activas = cuentas.filter(esta_activa=True).count()
    total_inactivas = cuentas.filter(esta_activa=False).count()
    
    # Calcular saldo actual para cada cuenta
    cuentas_con_saldo = []
    saldo_total_general = Decimal("0")
    
    for cuenta in cuentas:
        # Obtener totales de movimientos de esta cuenta (excluyendo anulados)
        totales = MovimientoFinanciero.objects.filter(
            cuenta=cuenta
        ).exclude(estado="anulado").aggregate(
            ingresos=Sum("monto", filter=Q(tipo="ingreso")),
            egresos=Sum("monto", filter=Q(tipo="egreso")),
        )
        
        ingresos = totales.get("ingresos") or Decimal("0")
        egresos = totales.get("egresos") or Decimal("0")
        saldo_actual = cuenta.saldo_inicial + ingresos - egresos
        
        # Agregar datos calculados
        cuentas_con_saldo.append({
            "cuenta": cuenta,
            "ingresos": ingresos,
            "egresos": egresos,
            "saldo_actual": saldo_actual,
        })
        
        # Sumar al total general (solo cuentas activas)
        if cuenta.esta_activa:
            saldo_total_general += saldo_actual

    context = {
        "cuentas": cuentas_con_saldo,
        "total_activas": total_activas,
        "total_inactivas": total_inactivas,
        "saldo_total_general": saldo_total_general,
    }
    return render(request, "finanzas_app/cuentas_listado.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.add_cuentafinanciera", raise_exception=True)
def cuenta_crear(request):




    """
    Crear una nueva cuenta financiera.
    """
    if request.method == "POST":
        form = CuentaFinancieraForm(request.POST)
        if form.is_valid():
            cuenta = form.save()
            messages.success(request, f"Cuenta «{cuenta.nombre}» creada correctamente.")
            return redirect("finanzas_app:cuentas_listado")
    else:
        form = CuentaFinancieraForm()

    context = {
        "form": form,
        "cuenta": None,
    }
    return render(request, "finanzas_app/cuenta_form.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.change_cuentafinanciera", raise_exception=True)
def cuenta_editar(request, pk):




    """
    Editar una cuenta financiera existente.
    """
    cuenta = get_object_or_404(CuentaFinanciera, pk=pk)

    if request.method == "POST":
        form = CuentaFinancieraForm(request.POST, instance=cuenta)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cuenta «{cuenta.nombre}» actualizada correctamente.")
            return redirect("finanzas_app:cuentas_listado")
    else:
        form = CuentaFinancieraForm(instance=cuenta)

    context = {
        "form": form,
        "cuenta": cuenta,
    }
    return render(request, "finanzas_app/cuenta_form.html", context)


@login_required
@require_POST
@permission_required("finanzas_app.change_cuentafinanciera", raise_exception=True)
def cuenta_toggle(request, pk):

    """
    Activar o desactivar una cuenta financiera.
    No eliminamos para mantener el historial de movimientos.
    """
    cuenta = get_object_or_404(CuentaFinanciera, pk=pk)
    
    # Toggle del estado
    cuenta.esta_activa = not cuenta.esta_activa
    cuenta.save()

    if cuenta.esta_activa:
        messages.success(request, f"Cuenta «{cuenta.nombre}» activada.")
    else:
        messages.warning(request, f"Cuenta «{cuenta.nombre}» desactivada.")

    return redirect("finanzas_app:cuentas_listado")


# ============================================
# CATEGORÍAS DE MOVIMIENTO - CRUD
# ============================================

@login_required
@require_GET
@permission_required("finanzas_app.view_categoriamovimiento", raise_exception=True)
def categorias_listado(request):

    """
    Listado de todas las categorías de movimiento.
    Permite filtrar por tipo (ingreso/egreso).
    """
    categorias = CategoriaMovimiento.objects.all().order_by("tipo", "nombre")
    
    # Filtro por tipo
    filtro_tipo = request.GET.get("tipo")
    if filtro_tipo in ["ingreso", "egreso"]:
        categorias = categorias.filter(tipo=filtro_tipo)
    
    # Contadores
    total_todas = CategoriaMovimiento.objects.count()
    total_ingresos = CategoriaMovimiento.objects.filter(tipo="ingreso").count()
    total_egresos = CategoriaMovimiento.objects.filter(tipo="egreso").count()

    context = {
        "categorias": categorias,
        "filtro_tipo": filtro_tipo,
        "total_todas": total_todas,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
    }
    return render(request, "finanzas_app/categorias_listado.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.add_categoriamovimiento", raise_exception=True)
def categoria_crear(request):
    """
    Crear una nueva categoría de movimiento.
    """
    if request.method == "POST":
        form = CategoriaMovimientoForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f"Categoría «{categoria.nombre}» creada correctamente.")
            return redirect("finanzas_app:categorias_listado")
    else:
        # Pre-seleccionar tipo si viene en la URL
        tipo_inicial = request.GET.get("tipo", "ingreso")
        form = CategoriaMovimientoForm(initial={"tipo": tipo_inicial})

    context = {
        "form": form,
        "categoria": None,
    }
    return render(request, "finanzas_app/categoria_form.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.change_categoriamovimiento", raise_exception=True)
def categoria_editar(request, pk):
    """
    Editar una categoría de movimiento existente.
    """
    categoria = get_object_or_404(CategoriaMovimiento, pk=pk)

    if request.method == "POST":
        form = CategoriaMovimientoForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, f"Categoría «{categoria.nombre}» actualizada correctamente.")
            return redirect("finanzas_app:categorias_listado")
    else:
        form = CategoriaMovimientoForm(instance=categoria)

    context = {
        "form": form,
        "categoria": categoria,
    }
    return render(request, "finanzas_app/categoria_form.html", context)


@login_required
@require_POST
@permission_required("finanzas_app.change_categoriamovimiento", raise_exception=True)
def categoria_toggle(request, pk):
    ...

    """
    Activar o desactivar una categoría.
    No eliminamos para mantener el historial de movimientos.
    """
    categoria = get_object_or_404(CategoriaMovimiento, pk=pk)
    
    # Toggle del estado
    categoria.activo = not categoria.activo
    categoria.save()

    if categoria.activo:
        messages.success(request, f"Categoría «{categoria.nombre}» activada.")
    else:
        messages.warning(request, f"Categoría «{categoria.nombre}» desactivada.")

    return redirect("finanzas_app:categorias_listado")


# ============================================
# MOVIMIENTOS FINANCIEROS
# ============================================

@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def movimientos_listado(request):



    """
    Listado de movimientos financieros con filtros básicos y totales.
    """
    movimientos = MovimientoFinanciero.objects.select_related(
        "cuenta", "categoria", "creado_por"
    ).exclude(estado="anulado").order_by("-fecha", "-creado_en")

    # --------- FILTROS ----------
    tipo = request.GET.get("tipo")
    cuenta_id = request.GET.get("cuenta")
    categoria_id = request.GET.get("categoria")
    q = request.GET.get("q")
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    if tipo == "transferencia":
        movimientos = movimientos.filter(es_transferencia=True)
    elif tipo in ["ingreso", "egreso"]:
        movimientos = movimientos.filter(tipo=tipo).exclude(es_transferencia=True)


    if cuenta_id:
        movimientos = movimientos.filter(cuenta_id=cuenta_id)

    if categoria_id:
        movimientos = movimientos.filter(categoria_id=categoria_id)

    if q:
        movimientos = movimientos.filter(
            Q(descripcion__icontains=q) |
            Q(referencia__icontains=q) |
            Q(persona_asociada__nombres__icontains=q) |
            Q(persona_asociada__apellidos__icontains=q) |
            Q(persona_asociada__codigo_miembro__icontains=q)
        )


    if fecha_desde:
        movimientos = movimientos.filter(fecha__gte=fecha_desde)

    if fecha_hasta:
        movimientos = movimientos.filter(fecha__lte=fecha_hasta)

    # --------- TOTALES ----------
    totales = movimientos.aggregate(
        total_ingresos=Sum("monto", filter=Q(tipo="ingreso")),
        total_egresos=Sum("monto", filter=Q(tipo="egreso")),
    )

    total_ingresos = totales.get("total_ingresos") or 0
    total_egresos = totales.get("total_egresos") or 0
    balance = total_ingresos - total_egresos

    cuentas = CuentaFinanciera.objects.filter(esta_activa=True).order_by("nombre")
    categorias = CategoriaMovimiento.objects.filter(activo=True).order_by("tipo", "nombre")

    context = {
        "movimientos": movimientos,
        "cuentas": cuentas,
        "categorias": categorias,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "balance": balance,
        "f_tipo": tipo or "",
        "f_cuenta": cuenta_id or "",
        "f_categoria": categoria_id or "",
        "f_q": q or "",
        "f_fecha_desde": fecha_desde or "",
        "f_fecha_hasta": fecha_hasta or "",
    }
    return render(request, "finanzas_app/movimientos_listado.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.add_movimientofinanciero", raise_exception=True)
def movimiento_crear(request):
 

    """
    Formulario para registrar un nuevo movimiento (ingreso o egreso).
    """
    if request.method == "POST":
        form = MovimientoFinancieroForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.creado_por = request.user
            mov.save()
            messages.success(request, "Movimiento registrado correctamente.")
            return redirect("finanzas_app:movimientos_listado")
    else:
        form = MovimientoFinancieroForm()

    context = {
        "form": form,
    }
    return render(request, "finanzas_app/ingreso_form.html", context)

@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.add_movimientofinanciero", raise_exception=True)
def ingreso_crear(request):


    """
    Formulario específico para registrar INGRESOS.
    """
    if request.method == "POST":
        form = MovimientoIngresoForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.tipo = "ingreso"
            mov.estado = "confirmado"
            mov.creado_por = request.user
            mov.save()
            messages.success(request, "Ingreso registrado y confirmado correctamente.")
            return redirect("/finanzas/movimientos/?tipo=ingreso")
    else:
        form = MovimientoIngresoForm(
            initial={
                "fecha": timezone.now().date(),
            }
        )

    context = {
        "form": form,
        "modo": "crear",
    }
    return render(request, "finanzas_app/ingreso_form.html", context)

@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.add_movimientofinanciero", raise_exception=True)
def egreso_crear(request):

    """
    Formulario específico para registrar EGRESOS.
    """
    if request.method == "POST":
        form = MovimientoEgresoForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.tipo = "egreso"
            mov.creado_por = request.user
            mov.save()
            messages.success(request, "Egreso registrado correctamente.")
            return redirect("/finanzas/movimientos/?tipo=egreso")
    else:
        form = MovimientoEgresoForm(
            initial={
                "fecha": timezone.now().date(),
            }
        )

    context = {
        "form": form,
        "modo": "crear",
    }
    return render(request, "finanzas_app/egreso.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.change_movimientofinanciero", raise_exception=True)
def movimiento_editar(request, pk):
    ...

    """
    Editar un movimiento financiero existente.
    - Si es ingreso: usa MovimientoIngresoForm + ingreso_form.html
    - Si es egreso: usa MovimientoEgresoForm + egreso.html
    """
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)
    if movimiento.estado == "anulado":
        messages.error(request, "Este movimiento está anulado y no se puede editar.")
        if movimiento.tipo == "ingreso":
            return redirect("finanzas_app:ingreso_detalle", pk=movimiento.pk)
        return redirect("finanzas_app:movimientos_listado")   
    # Elegimos formulario y plantilla según el tipo
    if movimiento.tipo == "ingreso":
        FormClass = MovimientoIngresoForm
        template_name = "finanzas_app/ingreso_form.html"
        redirect_url = "/finanzas/movimientos/?tipo=ingreso"
    else:
        FormClass = MovimientoEgresoForm
        template_name = "finanzas_app/egreso.html"
        redirect_url = "/finanzas/movimientos/?tipo=egreso"

    if request.method == "POST":
        form = FormClass(request.POST, instance=movimiento)
        if form.is_valid():
            form.save()
            messages.success(request, "Movimiento actualizado correctamente.")
            return redirect(redirect_url)
    else:
        form = FormClass(instance=movimiento)

    context = {
        "form": form,
        "movimiento": movimiento,
        "modo": "editar",
    }
    return render(request, template_name, context)

@login_required
@require_POST
@permission_required("finanzas_app.change_movimientofinanciero", raise_exception=True)
def movimiento_anular(request, pk):


    """
    Anular un movimiento financiero.
    Si es un egreso vinculado a una CxP, revierte el pago automáticamente.
    """
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)

    if movimiento.estado == "anulado":
        messages.warning(request, "Este movimiento ya está anulado.")
        return redirect("finanzas_app:movimientos_listado")

    if request.method == "POST":
        motivo = (request.POST.get("motivo") or "").strip()
        if not motivo:
            messages.error(request, "Debes indicar el motivo de la anulación.")
            return redirect("finanzas_app:movimiento_anular", pk=movimiento.pk)

        # ====================================================
        # NUEVO: Revertir pago si está vinculado a una CxP
        # ====================================================
        cxp = getattr(movimiento, 'cuenta_por_pagar', None)
        
        if cxp and movimiento.tipo == "egreso":
            # Restar el monto pagado de la CxP
            monto_a_revertir = movimiento.monto
            cxp.monto_pagado = max(
                Decimal("0"), 
                (cxp.monto_pagado or Decimal("0")) - monto_a_revertir
            )
            
            # Recalcular el estado de la CxP
            if cxp.monto_pagado <= Decimal("0"):
                cxp.estado = "pendiente"
            elif cxp.monto_pagado < cxp.monto_total:
                cxp.estado = "parcial"
            else:
                cxp.estado = "pagada"
            
            cxp.save()
            
            messages.info(
                request, 
                f"Se revirtió el pago de RD$ {monto_a_revertir:,.2f} de la cuenta por pagar #{cxp.pk}."
            )
        # ====================================================

        # Anular el movimiento
        movimiento.estado = "anulado"
        movimiento.motivo_anulacion = motivo
        movimiento.anulado_por = request.user
        movimiento.anulado_en = timezone.now()
        movimiento.save()

        messages.warning(request, f"Movimiento #{movimiento.pk} anulado correctamente.")
        return redirect("finanzas_app:movimientos_listado")

    # GET: mostrar formulario de confirmación
    context = {
        "modo": "movimiento",
        "movimiento": movimiento,
        "back_url": request.META.get("HTTP_REFERER") or reverse("finanzas_app:movimientos_listado"),
        # Indicar si tiene CxP vinculada para mostrar advertencia en el template
        "tiene_cxp": bool(getattr(movimiento, 'cuenta_por_pagar', None)),
    }

    return render(request, "finanzas_app/anulacion_confirmar.html", context)

@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def ingreso_detalle(request, pk):
    ...

    """
    Vista de detalle para un INGRESO.
    Muestra el movimiento en formato de ficha/documento.
    """
    ingreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="ingreso")

    context = {
        "ingreso": ingreso,
    }
    return render(request, "finanzas_app/ingreso_detalle.html", context)

from django.http import JsonResponse
from django.db.models import Q

from miembros_app.models import Miembro  # Ajusta si tu app se llama distinto


@login_required
@require_GET
@permission_required("finanzas_app.add_movimientofinanciero", raise_exception=True)
def buscar_miembros_finanzas(request):
    ...

    """
    Devuelve un JSON con miembros activos para el modal de búsqueda.
    Opcionalmente filtra por nombre/apellidos/código con ?q=.
    """
    q = request.GET.get("q", "").strip()

    miembros = Miembro.objects.filter(estado="activo")

    if q:
        miembros = miembros.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(codigo_miembro__icontains=q)
        )

    miembros = miembros.order_by("nombres", "apellidos")[:50]

    data = []
    for m in miembros:
        data.append(
            {
                "id": m.id,
                "nombre": f"{m.nombres} {m.apellidos}".strip(),
                "codigo": getattr(m, "codigo_miembro", "") or "",
            }
        )

    return JsonResponse({"resultados": data})
# ============================================
# TRANSFERENCIAS ENTRE CUENTAS
# ============================================

from .services import TransferenciaService
from .forms import TransferenciaForm


@login_required
@permission_required("finanzas_app.add_transferencia", raise_exception=True)
def transferencia_crear(request):
 
    """
    Vista para crear una transferencia entre cuentas.
    """
    if request.method == "POST":
        form = TransferenciaForm(request.POST)
        if form.is_valid():
            try:
                # Extraer datos del formulario
                cuenta_origen = form.cleaned_data["cuenta_origen"]
                cuenta_destino = form.cleaned_data["cuenta_destino"]
                monto = form.cleaned_data["monto"]
                fecha = form.cleaned_data["fecha"]
                descripcion = form.cleaned_data.get("descripcion", "")
                referencia = form.cleaned_data.get("referencia", "")
                
                # Crear la transferencia usando el servicio
                mov_envio, mov_recepcion = TransferenciaService.crear_transferencia(
                    cuenta_origen=cuenta_origen,
                    cuenta_destino=cuenta_destino,
                    monto=monto,
                    fecha=fecha,
                    usuario=request.user,
                    descripcion=descripcion,
                    referencia=referencia,
                    validar_saldo=True  # Validar que haya fondos
                )
                
                messages.success(
                    request,
                    f"Transferencia de {cuenta_origen.moneda} {monto} realizada exitosamente. "
                    f"De '{cuenta_origen.nombre}' a '{cuenta_destino.nombre}'."
                )
                return redirect("finanzas_app:transferencia_detalle", pk=mov_envio.pk)
            
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        # Pre-llenar fecha con hoy
        form = TransferenciaForm(initial={"fecha": timezone.now().date()})
    
    context = {
        "form": form,
    }
    return render(request, "finanzas_app/transferencia_form.html", context)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def transferencia_detalle(request, pk):


    """
    Vista de detalle de una transferencia.
    Muestra ambos movimientos (envío y recepción).
    """
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)
    
    # Verificar que sea una transferencia
    if not movimiento.es_transferencia:
        messages.warning(request, "Este movimiento no es una transferencia.")
        return redirect("finanzas_app:movimientos_listado")
    
    # Obtener el movimiento par
    movimiento_par = movimiento.get_transferencia_par()
    
    # Determinar cuál es el envío y cuál la recepción
    if movimiento.tipo == "egreso":
        mov_envio = movimiento
        mov_recepcion = movimiento_par
    else:
        mov_envio = movimiento_par
        mov_recepcion = movimiento
    
    context = {
        "transferencia": movimiento,
        "mov_envio": mov_envio,
        "mov_recepcion": mov_recepcion,
    }
    return render(request, "finanzas_app/transferencia_detalle.html", context)

@login_required
@require_POST
@permission_required("finanzas_app.change_movimientofinanciero", raise_exception=True)
def transferencia_anular(request, pk):


    """
    Anula una transferencia completa (ambos movimientos).
    Usa la plantilla unificada de anulación con estilo Odoo.
    """
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)

    # Validar que sea transferencia
    if not movimiento.es_transferencia:
        messages.error(request, "Este movimiento no es una transferencia.")
        return redirect("finanzas_app:movimientos_listado")

    # Obtener el par
    movimiento_par = movimiento.get_transferencia_par()
    if not movimiento_par:
        messages.error(request, "No se encontró el movimiento vinculado de esta transferencia.")
        return redirect("finanzas_app:movimientos_listado")

    # Determinar envío y recepción
    if movimiento.tipo == "egreso":
        mov_envio = movimiento
        mov_recepcion = movimiento_par
    else:
        mov_envio = movimiento_par
        mov_recepcion = movimiento

    # Si ya está anulada (con que uno lo esté, consideramos la transferencia anulada)
    if mov_envio.estado == "anulado" or mov_recepcion.estado == "anulado":
        messages.warning(request, "Esta transferencia ya está anulada.")
        return redirect("finanzas_app:transferencia_detalle", pk=mov_envio.pk)

    back_url = redirect("finanzas_app:transferencia_detalle", pk=mov_envio.pk).url

    if request.method == "POST":
        motivo = (request.POST.get("motivo") or "").strip()

        if not motivo:
            messages.error(request, "Debes indicar el motivo de la anulación.")
        else:
            # Anular ambos movimientos (misma auditoría)
            for mov in (mov_envio, mov_recepcion):
                mov.estado = "anulado"
                # Si estos campos existen en tu modelo, se guardan:
                if hasattr(mov, "motivo_anulacion"):
                    mov.motivo_anulacion = motivo
                if hasattr(mov, "anulado_por"):
                    mov.anulado_por = request.user
                if hasattr(mov, "fecha_anulacion"):
                    mov.fecha_anulacion = timezone.now()
                mov.save()

            messages.success(request, "Transferencia anulada correctamente.")
            return redirect("finanzas_app:transferencia_detalle", pk=mov_envio.pk)

    context = {
        "modo": "transferencia",
        "transferencia": mov_envio,  # usamos el EGRESO como “cabecera” visual
        "cuenta_origen": mov_envio.cuenta.nombre,
        "cuenta_destino": mov_recepcion.cuenta.nombre,
        "back_url": back_url,
    }
    return render(request, "finanzas_app/anulacion_confirmar.html", context)


# ============================================
# ADJUNTOS DE MOVIMIENTOS
# ============================================

from django.http import JsonResponse, FileResponse, Http404
from .models import AdjuntoMovimiento
from .validators import validar_archivo, validar_tamaño_total
import os


@login_required
@require_POST
@permission_required("finanzas_app.change_movimientofinanciero", raise_exception=True)
def subir_adjunto(request, movimiento_id):
    ...

    """
    Sube un archivo adjunto a un movimiento financiero.
    Retorna JSON para manejar con AJAX.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)
    
    # Verificar que el movimiento existe
    movimiento = get_object_or_404(MovimientoFinanciero, pk=movimiento_id)
    
    # Verificar que se subió un archivo
    if 'archivo' not in request.FILES:
        return JsonResponse({"success": False, "error": "No se recibió ningún archivo"}, status=400)
    
    archivo = request.FILES['archivo']
    
    try:
        # Validar el archivo
        validar_archivo(archivo)
        
        # Validar tamaño total
        validar_tamaño_total(movimiento, archivo.size)
        
        # Crear el adjunto
        adjunto = AdjuntoMovimiento.objects.create(
            movimiento=movimiento,
            archivo=archivo,
            nombre_original=archivo.name,
            tamaño=archivo.size,
            tipo_mime=archivo.content_type,
            subido_por=request.user
        )
        
        return JsonResponse({
            "success": True,
            "adjunto": {
                "id": adjunto.id,
                "nombre": adjunto.nombre_original,
                "tamaño": adjunto.tamaño_formateado(),
                "icono": adjunto.get_icono(),
                "url_descarga": f"/finanzas/adjuntos/{adjunto.id}/descargar/",
                "url_eliminar": f"/finanzas/adjuntos/{adjunto.id}/eliminar/",
                "puede_eliminar": adjunto.puede_eliminar(request.user),
                "es_imagen": adjunto.es_imagen(),
                "url_imagen": adjunto.archivo.url if adjunto.es_imagen() else None,
            }
        })
    
    except ValidationError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Error al subir archivo: {str(e)}"}, status=500)


@login_required
@require_POST
@permission_required("finanzas_app.change_movimientofinanciero", raise_exception=True)
def eliminar_adjunto(request, adjunto_id):
   

    """
    Elimina un adjunto de movimiento.
    Solo el usuario que lo subió o administradores pueden eliminarlo.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)
    
    adjunto = get_object_or_404(AdjuntoMovimiento, pk=adjunto_id)
    
    # Verificar permisos
    if not adjunto.puede_eliminar(request.user):
        return JsonResponse({
            "success": False, 
            "error": "No tienes permiso para eliminar este archivo"
        }, status=403)
    
    try:
        # Guardar info antes de eliminar
        nombre = adjunto.nombre_original
        
        # Eliminar archivo físico
        if adjunto.archivo:
            if os.path.isfile(adjunto.archivo.path):
                os.remove(adjunto.archivo.path)
        
        # Eliminar registro
        adjunto.delete()
        
        return JsonResponse({
            "success": True,
            "mensaje": f"Archivo '{nombre}' eliminado correctamente"
        })
    
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Error al eliminar archivo: {str(e)}"
        }, status=500)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def descargar_adjunto(request, adjunto_id):
    ...

    """
    Descarga un archivo adjunto.
    """
    adjunto = get_object_or_404(AdjuntoMovimiento, pk=adjunto_id)
    
    # Verificar que el archivo existe
    if not adjunto.archivo:
        raise Http404("Archivo no encontrado")
    
    try:
        # Abrir el archivo
        archivo = open(adjunto.archivo.path, 'rb')
        response = FileResponse(archivo)
        
        # Configurar headers para descarga
        response['Content-Type'] = adjunto.tipo_mime or 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{adjunto.nombre_original}"'
        response['Content-Length'] = adjunto.tamaño
        
        return response
    
    except FileNotFoundError:
        raise Http404("Archivo no encontrado en el servidor")
    except Exception as e:
        raise Http404(f"Error al descargar archivo: {str(e)}")


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def listar_adjuntos(request, movimiento_id):
    ...

    """
    Lista todos los adjuntos de un movimiento (JSON para AJAX).
    """
    movimiento = get_object_or_404(MovimientoFinanciero, pk=movimiento_id)
    
    adjuntos = AdjuntoMovimiento.objects.filter(movimiento=movimiento)
    
    data = {
        "success": True,
        "adjuntos": [
            {
                "id": adj.id,
                "nombre": adj.nombre_original,
                "tamaño": adj.tamaño_formateado(),
                "icono": adj.get_icono(),
                "url_descarga": f"/finanzas/adjuntos/{adj.id}/descargar/",
                "url_eliminar": f"/finanzas/adjuntos/{adj.id}/eliminar/",
                "puede_eliminar": adj.puede_eliminar(request.user),
                "es_imagen": adj.es_imagen(),
                "url_imagen": adj.archivo.url if adj.es_imagen() else None,
                "subido_por": adj.subido_por.get_full_name() if adj.subido_por else "Sistema",
                "subido_en": adj.subido_en.strftime("%d/%m/%Y %H:%M"),
            }
            for adj in adjuntos
        ]
    }
    
    return JsonResponse(data)

@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def ingreso_recibo(request, pk):
    ...

    """
    Vista SOLO para imprimir el recibo de un ingreso (formato 80mm).
    """
    ingreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="ingreso")

    context = {
        "ingreso": ingreso,
        "auto_print": True,  # para que el template pueda disparar window.print()
    }
    return render(request, "finanzas_app/recibos/ingreso_recibo.html", context)



@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def ingreso_general_pdf(request, pk):


    ingreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="ingreso")
    CFG = get_config()
    return render(request, "finanzas_app/recibos/ingreso_general_pdf.html", {"ingreso": ingreso, "CFG": CFG})

@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def transferencia_general_pdf(request, pk):
  

    """
    Vista GENERAL PDF de una transferencia.
    Usa la misma lógica que transferencia_detalle,
    pero renderiza la plantilla limpia de reporte.
    """
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)

    if not movimiento.es_transferencia:
        messages.warning(request, "Este movimiento no es una transferencia.")
        return redirect("finanzas_app:movimientos_listado")

    movimiento_par = movimiento.get_transferencia_par()

    if movimiento.tipo == "egreso":
        mov_envio = movimiento
        mov_recepcion = movimiento_par
    else:
        mov_envio = movimiento_par
        mov_recepcion = movimiento

    CFG = get_config()

    return render(
        request,
        "finanzas_app/recibos/transferencia_general_pdf.html",
        {
            "transferencia": movimiento,
            "mov_envio": mov_envio,
            "mov_recepcion": mov_recepcion,
            "CFG": CFG,
        },
    )


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def egreso_detalle(request, pk):
  

    egreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="egreso")
    return render(request, "finanzas_app/egreso_detalle.html", {"egreso": egreso})

@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def movimientos_listado_print(request):
    """
    Vista SOLO para imprimir el listado de movimientos según los filtros actuales.
    Reutiliza la misma lógica de filtros que movimientos_listado.
    """
    movimientos = MovimientoFinanciero.objects.select_related(
        "cuenta", "categoria", "creado_por"
    ).exclude(estado="anulado").order_by("-fecha", "-creado_en")

    # --------- FILTROS (MISMA LÓGICA) ----------
    tipo = request.GET.get("tipo")
    cuenta_id = request.GET.get("cuenta")
    categoria_id = request.GET.get("categoria")
    q = request.GET.get("q")
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    if tipo in ["ingreso", "egreso"]:
        movimientos = movimientos.filter(tipo=tipo)

    if cuenta_id:
        movimientos = movimientos.filter(cuenta_id=cuenta_id)

    if categoria_id:
        movimientos = movimientos.filter(categoria_id=categoria_id)

    if q:
        movimientos = movimientos.filter(
            Q(descripcion__icontains=q) |
            Q(referencia__icontains=q) |
            Q(persona_asociada__nombres__icontains=q) |
            Q(persona_asociada__apellidos__icontains=q) |
            Q(persona_asociada__codigo_miembro__icontains=q)
        )

    if fecha_desde:
        movimientos = movimientos.filter(fecha__gte=fecha_desde)

    if fecha_hasta:
        movimientos = movimientos.filter(fecha__lte=fecha_hasta)

    # --------- TOTALES ----------
    totales = movimientos.aggregate(
        total_ingresos=Sum("monto", filter=Q(tipo="ingreso")),
        total_egresos=Sum("monto", filter=Q(tipo="egreso")),
    )

    total_ingresos = totales.get("total_ingresos") or 0
    total_egresos = totales.get("total_egresos") or 0
    balance = total_ingresos - total_egresos

    # Para mostrar etiquetas bonitas de filtros (opcional pero pro)
    cuenta_obj = None
    categoria_obj = None
    if cuenta_id:
        cuenta_obj = CuentaFinanciera.objects.filter(pk=cuenta_id).first()
    if categoria_id:
        categoria_obj = CategoriaMovimiento.objects.filter(pk=categoria_id).first()

    # Config general (tu base de reporte suele necesitarlo)
    CFG = get_config()

    context = {
        "movimientos": movimientos,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "balance": balance,

        # filtros para el encabezado
        "f_tipo": tipo or "",
        "f_cuenta": cuenta_id or "",
        "f_categoria": categoria_id or "",
        "f_q": q or "",
        "f_fecha_desde": fecha_desde or "",
        "f_fecha_hasta": fecha_hasta or "",

        # objetos para mostrar nombres (bonito)
        "cuenta_obj": cuenta_obj,
        "categoria_obj": categoria_obj,

        "CFG": CFG,
        "auto_print": True,
    }
    return render(request, "finanzas_app/reportes/movimientos_listado_print.html", context)

@login_required
def reporte_resumen_mensual(request):
    """
    Reporte imprimible: Cierre mensual (ingresos, egresos, balance).
    Filtros:
      - year, month (obligatorio por defecto al mes actual)
      - cuenta (opcional)
      - incluir_transferencias=1 (opcional)
      - agrupar=1 (opcional: muestra resumen por categoría)
      - print=1 (opcional: dispara window.print())
    """
    hoy = timezone.now().date()

    # ---- filtros base ----
    year = request.GET.get("year")
    month = request.GET.get("month")
    cuenta_id = (request.GET.get("cuenta") or "").strip()

    incluir_transferencias = request.GET.get("incluir_transferencias") in ("1", "true", "True", "on")
    agrupar = request.GET.get("agrupar") in ("1", "true", "True", "on")

    auto_print = request.GET.get("print") in ("1", "true", "True")

    try:
        year = int(year) if year else hoy.year
        month = int(month) if month else hoy.month
        if month < 1 or month > 12:
            raise ValueError
    except Exception:
        year = hoy.year
        month = hoy.month

    # ---- query del mes (excluyendo anulados) ----
    qs_mes = MovimientoFinanciero.objects.filter(
        fecha__year=year,
        fecha__month=month,
    ).exclude(estado="anulado")

    # filtro por cuenta (si viene)
    cuenta_obj = None
    if cuenta_id:
        qs_mes = qs_mes.filter(cuenta_id=cuenta_id)
        cuenta_obj = CuentaFinanciera.objects.filter(pk=cuenta_id).first()

    # ---- ingresos/egresos (operativo vs incluyendo transferencias) ----
    if incluir_transferencias:
        qs_balance = qs_mes
    else:
        qs_balance = qs_mes.exclude(es_transferencia=True)

    totales = qs_balance.aggregate(
        ingresos=Sum("monto", filter=Q(tipo="ingreso")),
        egresos=Sum("monto", filter=Q(tipo="egreso")),
    )

    ingresos_mes = totales.get("ingresos") or Decimal("0")
    egresos_mes = totales.get("egresos") or Decimal("0")
    balance_mes = ingresos_mes - egresos_mes

    # ---- transferencias del mes (informativo) ----
    qs_transf = qs_mes.filter(es_transferencia=True)
    transf_totales = qs_transf.aggregate(
        transf_egreso=Sum("monto", filter=Q(tipo="egreso")),
        transf_ingreso=Sum("monto", filter=Q(tipo="ingreso")),
    )
    transf_egreso = transf_totales.get("transf_egreso") or Decimal("0")
    transf_ingreso = transf_totales.get("transf_ingreso") or Decimal("0")

    # ---- agrupación por categoría (opcional) ----
    resumen_por_categoria = []
    if agrupar:
        # OJO: si NO incluimos transferencias, también las excluimos aquí para coherencia
        qs_cat = qs_balance.values("tipo", "categoria__nombre").annotate(total=Sum("monto")).order_by("tipo", "-total")
        for row in qs_cat:
            resumen_por_categoria.append({
                "tipo": row["tipo"],
                "categoria": row["categoria__nombre"] or "Sin categoría",
                "total": row["total"] or Decimal("0"),
            })

    # ---- combos para el form ----
    cuentas = CuentaFinanciera.objects.filter(esta_activa=True).order_by("nombre")

    NOMBRES_MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    mes_label = f"{NOMBRES_MESES[month]} {year}"

    CFG = get_config()

    context = {
        "CFG": CFG,
        "auto_print": auto_print,
        "fecha_hoy": hoy,

        # filtros actuales
        "year": year,
        "month": month,
        "mes_label": mes_label,
        "cuenta_id": cuenta_id,
        "cuenta_obj": cuenta_obj,
        "incluir_transferencias": incluir_transferencias,
        "agrupar": agrupar,

        # datos
        "ingresos_mes": ingresos_mes,
        "egresos_mes": egresos_mes,
        "balance_mes": balance_mes,
        "transf_ingreso": transf_ingreso,
        "transf_egreso": transf_egreso,
        "resumen_por_categoria": resumen_por_categoria,

        # selects
        "cuentas": cuentas,
        "meses": [(i, NOMBRES_MESES[i]) for i in range(1, 13)],
    }
    return render(request, "finanzas_app/reportes/resumen_mensual.html", context)

@login_required
def reportes_home(request):
    """
    Home de reportes del módulo Finanzas (estilo tarjetas).
    """
    return render(request, "finanzas_app/reportes/reportes_home.html")


@login_required
def reporte_resumen_por_cuenta(request):
    """
    Reporte: Resumen por cuenta (ingresos, egresos, balance) por mes/año.
    Filtros:
      - year, month (por defecto mes actual)
      - incluir_transferencias=1 (opcional)
      - print=1 (opcional)
    """
    hoy = timezone.now().date()

    year = request.GET.get("year")
    month = request.GET.get("month")
    incluir_transferencias = request.GET.get("incluir_transferencias") in ("1", "true", "True", "on")
    auto_print = request.GET.get("print") in ("1", "true", "True")

    try:
        year = int(year) if year else hoy.year
        month = int(month) if month else hoy.month
        if month < 1 or month > 12:
            raise ValueError
    except Exception:
        year = hoy.year
        month = hoy.month

    qs = MovimientoFinanciero.objects.filter(
        fecha__year=year,
        fecha__month=month,
    ).exclude(estado="anulado")

    if not incluir_transferencias:
        qs = qs.exclude(es_transferencia=True)

    # Agrupar por cuenta + sumar por tipo
    filas = (qs.values("cuenta_id", "cuenta__nombre")
               .annotate(
                    ingresos=Sum("monto", filter=Q(tipo="ingreso")),
                    egresos=Sum("monto", filter=Q(tipo="egreso")),
                )
               .order_by("cuenta__nombre"))

    data = []
    total_ing = Decimal("0")
    total_egr = Decimal("0")

    for f in filas:
        ing = f["ingresos"] or Decimal("0")
        egr = f["egresos"] or Decimal("0")
        bal = ing - egr

        total_ing += ing
        total_egr += egr

        data.append({
            "cuenta": f["cuenta__nombre"] or "Sin cuenta",
            "ingresos": ing,
            "egresos": egr,
            "balance": bal,
        })

    total_balance = total_ing - total_egr

    NOMBRES_MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    mes_label = f"{NOMBRES_MESES[month]} {year}"

    CFG = get_config()

    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,

        "year": year,
        "month": month,
        "mes_label": mes_label,
        "incluir_transferencias": incluir_transferencias,
        "meses": [(i, NOMBRES_MESES[i]) for i in range(1, 13)],

        "data": data,
        "total_ingresos": total_ing,
        "total_egresos": total_egr,
        "total_balance": total_balance,
    }
    return render(request, "finanzas_app/reportes/resumen_por_cuenta.html", context)


@login_required
def reporte_resumen_por_categoria(request):
    """
    Reporte: Resumen por categoría (totales de ingresos y egresos agrupados).
    Filtros:
      - year, month (por defecto mes actual)
      - cuenta (opcional)
      - incluir_transferencias=1 (opcional)
      - print=1 (opcional)
    """
    hoy = timezone.now().date()

    year = request.GET.get("year")
    month = request.GET.get("month")
    cuenta_id = (request.GET.get("cuenta") or "").strip()

    incluir_transferencias = request.GET.get("incluir_transferencias") in ("1", "true", "True", "on")
    auto_print = request.GET.get("print") in ("1", "true", "True")

    try:
        year = int(year) if year else hoy.year
        month = int(month) if month else hoy.month
        if month < 1 or month > 12:
            raise ValueError
    except Exception:
        year = hoy.year
        month = hoy.month

    qs = MovimientoFinanciero.objects.filter(
        fecha__year=year,
        fecha__month=month,
    ).exclude(estado="anulado")

    cuenta_obj = None
    if cuenta_id:
        qs = qs.filter(cuenta_id=cuenta_id)
        cuenta_obj = CuentaFinanciera.objects.filter(pk=cuenta_id).first()

    if not incluir_transferencias:
        qs = qs.exclude(es_transferencia=True)

    # Agrupar por categoría + sumar por tipo
    filas = (
        qs.values("categoria_id", "categoria__nombre")
          .annotate(
              ingresos=Sum("monto", filter=Q(tipo="ingreso")),
              egresos=Sum("monto", filter=Q(tipo="egreso")),
          )
          .order_by("categoria__nombre")
    )

    data = []
    total_ing = Decimal("0")
    total_egr = Decimal("0")

    for f in filas:
        ing = f["ingresos"] or Decimal("0")
        egr = f["egresos"] or Decimal("0")
        bal = ing - egr

        total_ing += ing
        total_egr += egr

        data.append({
            "categoria": f["categoria__nombre"] or "Sin categoría",
            "ingresos": ing,
            "egresos": egr,
            "balance": bal,
        })

    total_balance = total_ing - total_egr

    NOMBRES_MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    mes_label = f"{NOMBRES_MESES[month]} {year}"

    cuentas = CuentaFinanciera.objects.filter(esta_activa=True).order_by("nombre")
    CFG = get_config()

    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,

        "year": year,
        "month": month,
        "mes_label": mes_label,
        "meses": [(i, NOMBRES_MESES[i]) for i in range(1, 13)],

        "cuentas": cuentas,
        "cuenta_id": cuenta_id,
        "cuenta_obj": cuenta_obj,

        "incluir_transferencias": incluir_transferencias,

        "data": data,
        "total_ingresos": total_ing,
        "total_egresos": total_egr,
        "total_balance": total_balance,
    }
    return render(request, "finanzas_app/reportes/resumen_por_categoria.html", context)


@login_required
def reporte_movimientos_anulados(request):
    """
    Reporte: Movimientos anulados (auditoría).
    Filtros:
      - year, month (por defecto mes actual)
      - tipo (opcional: ingreso/egreso/transferencia)
      - cuenta (opcional)
      - print=1 (opcional)
    """
    hoy = timezone.now().date()

    year = request.GET.get("year")
    month = request.GET.get("month")
    tipo = (request.GET.get("tipo") or "").strip()
    cuenta_id = (request.GET.get("cuenta") or "").strip()
    auto_print = request.GET.get("print") in ("1", "true", "True")

    try:
        year = int(year) if year else hoy.year
        month = int(month) if month else hoy.month
        if month < 1 or month > 12:
            raise ValueError
    except Exception:
        year = hoy.year
        month = hoy.month

    qs = MovimientoFinanciero.objects.select_related(
        "cuenta", "categoria", "creado_por", "anulado_por"
    ).filter(
        estado="anulado",
        fecha__year=year,
        fecha__month=month,
    ).order_by("-anulado_en", "-fecha", "-id")

    # filtro por cuenta
    cuenta_obj = None
    if cuenta_id:
        qs = qs.filter(cuenta_id=cuenta_id)
        cuenta_obj = CuentaFinanciera.objects.filter(pk=cuenta_id).first()

    # filtro por tipo
    # - ingreso / egreso (campo tipo)
    # - transferencia (es_transferencia=True)
    if tipo in ("ingreso", "egreso"):
        qs = qs.filter(tipo=tipo, es_transferencia=False)
    elif tipo == "transferencia":
        qs = qs.filter(es_transferencia=True)

    # combos
    cuentas = CuentaFinanciera.objects.filter(esta_activa=True).order_by("nombre")
    CFG = get_config()

    NOMBRES_MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    mes_label = f"{NOMBRES_MESES[month]} {year}"

    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,

        "year": year,
        "month": month,
        "mes_label": mes_label,
        "meses": [(i, NOMBRES_MESES[i]) for i in range(1, 13)],

        "cuentas": cuentas,
        "cuenta_id": cuenta_id,
        "cuenta_obj": cuenta_obj,

        "tipo": tipo,
        "qs": qs,
    }
    return render(request, "finanzas_app/reportes/movimientos_anulados.html", context)


@login_required
def reporte_transferencias(request):
    """
    Reporte de auditoría de transferencias.
    Cada transferencia se muestra como una sola fila
    (origen -> destino) usando transferencia_id.
    """
    hoy = timezone.now().date()

    year = request.GET.get("year")
    month = request.GET.get("month")
    cuenta_id = (request.GET.get("cuenta") or "").strip()
    estado = (request.GET.get("estado") or "").strip()  # activo / anulado / ""
    auto_print = request.GET.get("print") in ("1", "true", "True")

    try:
        year = int(year) if year else hoy.year
        month = int(month) if month else hoy.month
        if month < 1 or month > 12:
            raise ValueError
    except Exception:
        year = hoy.year
        month = hoy.month

    # Base: solo transferencias
    qs = (
        MovimientoFinanciero.objects
        .select_related("cuenta", "creado_por", "anulado_por")
        .filter(
            es_transferencia=True,
            fecha__year=year,
            fecha__month=month,
        )
        .order_by("transferencia_id", "tipo")
    )

    if cuenta_id:
        qs = qs.filter(cuenta_id=cuenta_id)

    if estado == "activo":
        qs = qs.exclude(estado="anulado")
    elif estado == "anulado":
        qs = qs.filter(estado="anulado")

    # Agrupar por transferencia_id
    agrupadas = defaultdict(dict)

    for mov in qs:
        grupo = agrupadas[mov.transferencia_id]
        grupo["fecha"] = mov.fecha
        grupo["referencia"] = mov.referencia
        grupo["descripcion"] = mov.descripcion
        grupo["creado_por"] = mov.creado_por
        grupo["estado"] = mov.estado
        grupo["anulado_en"] = mov.anulado_en
        grupo["anulado_por"] = mov.anulado_por

        if mov.tipo == "egreso":
            grupo["origen"] = mov.cuenta
            grupo["monto"] = mov.monto
        elif mov.tipo == "ingreso":
            grupo["destino"] = mov.cuenta
            grupo["monto"] = mov.monto

    transferencias = []
    for tid, data in agrupadas.items():
        transferencias.append({
            "id": tid,
            **data,
        })

    cuentas = CuentaFinanciera.objects.filter(esta_activa=True).order_by("nombre")
    CFG = get_config()

    NOMBRES_MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    mes_label = f"{NOMBRES_MESES[month]} {year}"

    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,

        "year": year,
        "month": month,
        "mes_label": mes_label,
        "meses": [(i, NOMBRES_MESES[i]) for i in range(1, 13)],

        "cuentas": cuentas,
        "cuenta_id": cuenta_id,
        "estado": estado,

        "transferencias": transferencias,
    }
    return render(
        request,
        "finanzas_app/reportes/transferencias.html",
        context
    )


# ==========================================================
# CUENTAS POR PAGAR (CxP) – CRUD BÁSICO (SIN PAGOS AÚN)
# ==========================================================

# Reemplazar la vista cxp_list en views.py
# Reemplazar la vista cxp_list en views.py

@login_required
@require_GET
@permission_required("finanzas_app.view_cuentaporpagar", raise_exception=True)
def cxp_list(request):
    estado = (request.GET.get("estado") or "").strip()
    q = (request.GET.get("q") or "").strip()
    proveedor_id = (request.GET.get("proveedor") or "").strip()
    fecha_desde = (request.GET.get("fecha_desde") or "").strip()
    fecha_hasta = (request.GET.get("fecha_hasta") or "").strip()

    qs = CuentaPorPagar.objects.select_related(
        "proveedor", "categoria", "cuenta_sugerida"
    ).all()

    if estado:
        qs = qs.filter(estado=estado)

    if q:
        qs = qs.filter(
            Q(concepto__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(referencia__icontains=q) |
            Q(proveedor__nombre__icontains=q)
        )

    if proveedor_id:
        qs = qs.filter(proveedor_id=proveedor_id)

    if fecha_desde:
        qs = qs.filter(fecha_emision__gte=fecha_desde)

    if fecha_hasta:
        qs = qs.filter(fecha_emision__lte=fecha_hasta)

    qs = qs.order_by("-fecha_emision", "-creado_en")

    # Calcular totales
    totales = qs.aggregate(
        total_monto=Sum("monto_total"),
        total_pagado=Sum("monto_pagado"),
    )
    
    total_monto = totales.get("total_monto") or Decimal("0")
    total_pagado = totales.get("total_pagado") or Decimal("0")
    total_pendiente = total_monto - total_pagado

    # Proveedores para el filtro
    proveedores = ProveedorFinanciero.objects.filter(activo=True).order_by("nombre")

    # Agregar propiedades de vencimiento a cada item
    hoy = datetime.date.today()
    items_con_vencimiento = []
    for item in qs:
        # Agregar propiedades calculadas
        item.esta_vencida = (
            item.fecha_vencimiento and 
            item.fecha_vencimiento < hoy and 
            item.estado not in ("pagada", "cancelada")
        )
        item.proxima_a_vencer = (
            item.fecha_vencimiento and 
            not item.esta_vencida and
            item.fecha_vencimiento <= hoy + datetime.timedelta(days=7) and
            item.estado not in ("pagada", "cancelada")
        )
        items_con_vencimiento.append(item)

    context = {
        "items": items_con_vencimiento,
        "estado": estado,
        "q": q,
        "proveedor": proveedor_id,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "ESTADOS": CuentaPorPagar.ESTADO_CHOICES,
        "proveedores": proveedores,
        "total_pendiente": total_pendiente,
        "total_pagado": total_pagado,
    }
    return render(request, "finanzas_app/cxp/lista.html", context)

@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.add_cuentaporpagar", raise_exception=True)
def cxp_create(request):
    if request.method == "POST":
        form = CuentaPorPagarForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.creado_por = request.user
            obj.estado = "pendiente"
            obj.monto_pagado = obj.monto_pagado or 0
            obj.save()

            messages.success(request, "✅ Cuenta por pagar creada correctamente.")
            return redirect("finanzas_app:cxp_detail", pk=obj.pk)
    else:
        form = CuentaPorPagarForm()

    return render(request, "finanzas_app/cxp/crear.html", {"form": form})

# Reemplazar la vista cxp_detail en views.py

@login_required
@require_GET
@permission_required("finanzas_app.view_cuentaporpagar", raise_exception=True)
def cxp_detail(request, pk):
    obj = get_object_or_404(
        CuentaPorPagar.objects.select_related(
            "proveedor", "categoria", "cuenta_sugerida"
        ),
        pk=pk
    )

    # Obtener historial de pagos vinculados a esta CxP
    pagos = MovimientoFinanciero.objects.filter(
        cuenta_por_pagar=obj
    ).select_related("cuenta", "creado_por").order_by("-fecha", "-creado_en")

    return render(request, "finanzas_app/cxp/detalle.html", {
        "obj": obj,
        "pagos": pagos,
    })


# ----------------------------------------------------------
# PROVEEDORES (mínimo para poder crear CxP sin fricción)
# ----------------------------------------------------------

@login_required
@require_GET
@permission_required("finanzas_app.view_proveedorfinanciero", raise_exception=True)
def proveedores_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = ProveedorFinanciero.objects.all()
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(telefono__icontains=q) |
            Q(email__icontains=q)
        )
    qs = qs.order_by("nombre")

    return render(request, "finanzas_app/cxp/proveedores_lista.html", {"items": qs, "q": q})


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.add_proveedorfinanciero", raise_exception=True)
def proveedores_create(request):
    if request.method == "POST":
        form = ProveedorFinancieroForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "✅ Proveedor creado correctamente.")
            return redirect("finanzas_app:proveedores_list")
    else:
        form = ProveedorFinancieroForm()

    return render(request, "finanzas_app/cxp/proveedores_crear.html", {"form": form})

@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.change_proveedorfinanciero", raise_exception=True)
def proveedores_editar(request, pk):
    proveedor = get_object_or_404(ProveedorFinanciero, pk=pk)

    if request.method == "POST":
        form = ProveedorFinancieroForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Proveedor actualizado correctamente.")
            return redirect("finanzas_app:proveedores_list")
    else:
        form = ProveedorFinancieroForm(instance=proveedor)

    # Reutilizamos EXACTAMENTE la misma plantilla del crear
    return render(
        request,
        "finanzas_app/cxp/proveedores_crear.html",
        {
            "form": form,
            "proveedor": proveedor,
            "modo": "editar",
        },
    )

@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.change_cuentaporpagar", raise_exception=True)
def cxp_edit(request, pk):
    """
    Editar una Cuenta por Pagar existente.
    No permite editar si está PAGADA.
    """
    cxp = get_object_or_404(CuentaPorPagar, pk=pk)

    # Regla de negocio: no editar si ya está pagada
    if cxp.estado == "pagada":
        messages.warning(
            request,
            "Esta cuenta ya está pagada y no puede ser modificada."
        )
        return redirect("finanzas_app:cxp_detail", pk=cxp.pk)

    if request.method == "POST":
        form = CuentaPorPagarForm(request.POST, instance=cxp)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Cuenta por pagar actualizada correctamente."
            )
            return redirect("finanzas_app:cxp_detail", pk=cxp.pk)
    else:
        form = CuentaPorPagarForm(instance=cxp)

    context = {
        "form": form,
        "obj": cxp,
        "modo": "editar",
    }

    return render(
        request,
        "finanzas_app/cxp_form.html",
        context
    )

# Vista para agregar a finanzas_app/views.py
# Vista para agregar a finanzas_app/views.py

@login_required
@transaction.atomic
def cxp_pagar(request, pk):
    """
    Registrar un pago (total o parcial) a una Cuenta por Pagar.
    Crea un MovimientoFinanciero tipo egreso y actualiza la CxP.
    """
    cxp = get_object_or_404(CuentaPorPagar, pk=pk)

    # No permitir pagar si ya está pagada o cancelada
    if cxp.estado in ("pagada", "cancelada"):
        messages.warning(request, "Esta cuenta ya está pagada o cancelada.")
        return redirect("finanzas_app:cxp_detail", pk=cxp.pk)

    # Cuentas activas para el select
    cuentas = CuentaFinanciera.objects.filter(esta_activa=True).order_by("nombre")

    if request.method == "POST":
        # Obtener datos del form
        monto_str = request.POST.get("monto", "").strip().replace(",", "")
        cuenta_id = request.POST.get("cuenta", "").strip()
        fecha_str = request.POST.get("fecha", "").strip()
        referencia = request.POST.get("referencia", "").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        forma_pago = request.POST.get("forma_pago", "efectivo").strip()

        errores = []

        # Validar monto
        try:
            monto = Decimal(monto_str)
            if monto <= 0:
                errores.append("El monto debe ser mayor a cero.")
            elif monto > cxp.saldo_pendiente:
                errores.append(f"El monto no puede exceder el saldo pendiente (RD$ {cxp.saldo_pendiente:,.2f}).")
        except:
            errores.append("Monto inválido.")
            monto = None

        # Validar cuenta
        try:
            cuenta = CuentaFinanciera.objects.get(pk=cuenta_id, esta_activa=True)
        except CuentaFinanciera.DoesNotExist:
            errores.append("Seleccione una cuenta válida.")
            cuenta = None

        # Validar fecha
        try:
            fecha = datetime.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except:
            errores.append("Fecha inválida.")
            fecha = None

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            # Crear el movimiento de egreso vinculado a la CxP
            movimiento = MovimientoFinanciero.objects.create(
                fecha=fecha,
                tipo="egreso",
                cuenta=cuenta,
                categoria=cxp.categoria,
                monto=monto,
                descripcion=descripcion or f"Pago CxP #{cxp.pk} - {cxp.proveedor.nombre}",
                referencia=referencia,
                forma_pago=forma_pago,
                estado="confirmado",
                creado_por=request.user,
                cuenta_por_pagar=cxp,  # 👈 Vinculamos el pago con la CxP
            )

            # Actualizar la CxP
            cxp.monto_pagado = (cxp.monto_pagado or Decimal("0")) + monto
            
            if cxp.monto_pagado >= cxp.monto_total:
                cxp.estado = "pagada"
            else:
                cxp.estado = "parcial"
            
            cxp.save()

            messages.success(
                request,
                f"✅ Pago de RD$ {monto:,.2f} registrado correctamente."
            )
            return redirect("finanzas_app:cxp_detail", pk=cxp.pk)

    # GET: valores por defecto
    fecha_hoy = datetime.date.today()

    context = {
        "cxp": cxp,
        "cuentas": cuentas,
        "fecha_hoy": fecha_hoy,
        "FORMA_PAGO_CHOICES": MovimientoFinanciero.FORMA_PAGO_CHOICES,
    }

    return render(request, "finanzas_app/cxp/pagar.html", context)


# ============================================
# REPORTES DE CUENTAS POR PAGAR (CxP)
# ============================================



# ----------------------------------------------------------
# REPORTE: RESUMEN GENERAL DE CxP
# ----------------------------------------------------------
@login_required
def reporte_cxp(request):
    """
    Reporte general de Cuentas por Pagar con filtros.
    Filtros:
      - estado (pendiente, parcial, pagada, vencida, cancelada)
      - proveedor
      - categoria
      - fecha_desde, fecha_hasta (fecha_emision)
      - print=1 (modo impresión)
    """
    hoy = timezone.now().date()
    
    # Parámetros de filtro
    estado = (request.GET.get("estado") or "").strip()
    proveedor_id = (request.GET.get("proveedor") or "").strip()
    categoria_id = (request.GET.get("categoria") or "").strip()
    fecha_desde = (request.GET.get("fecha_desde") or "").strip()
    fecha_hasta = (request.GET.get("fecha_hasta") or "").strip()
    auto_print = request.GET.get("print") in ("1", "true", "True")
    
    # QuerySet base
    qs = CuentaPorPagar.objects.select_related(
        "proveedor", "categoria"
    ).all()
    
    # Aplicar filtros
    if estado:
        qs = qs.filter(estado=estado)
    
    if proveedor_id:
        qs = qs.filter(proveedor_id=proveedor_id)
    
    if categoria_id:
        qs = qs.filter(categoria_id=categoria_id)
    
    if fecha_desde:
        qs = qs.filter(fecha_emision__gte=fecha_desde)
    
    if fecha_hasta:
        qs = qs.filter(fecha_emision__lte=fecha_hasta)
    
    qs = qs.order_by("-fecha_emision", "-creado_en")
    
    # Calcular totales
    totales = qs.aggregate(
        total_monto=Sum("monto_total"),
        total_pagado=Sum("monto_pagado"),
        cantidad=Count("id"),
    )
    
    total_monto = totales.get("total_monto") or Decimal("0")
    total_pagado = totales.get("total_pagado") or Decimal("0")
    total_pendiente = total_monto - total_pagado
    cantidad = totales.get("cantidad") or 0
    
    # Resumen por estado
    resumen_estados = qs.values("estado").annotate(
        cantidad=Count("id"),
        monto=Sum("monto_total"),
        pagado=Sum("monto_pagado"),
    ).order_by("estado")
    
    # Agregar propiedades de vencimiento a cada item
    items = []
    for item in qs:
        item.esta_vencida = (
            item.fecha_vencimiento and 
            item.fecha_vencimiento < hoy and 
            item.estado not in ("pagada", "cancelada")
        )
        item.dias_vencida = 0
        if item.esta_vencida:
            item.dias_vencida = (hoy - item.fecha_vencimiento).days
        
        item.proxima_a_vencer = (
            item.fecha_vencimiento and 
            not item.esta_vencida and
            item.fecha_vencimiento <= hoy + datetime.timedelta(days=7) and
            item.estado not in ("pagada", "cancelada")
        )
        items.append(item)
    
    # Listas para filtros
    proveedores = ProveedorFinanciero.objects.filter(activo=True).order_by("nombre")
    categorias = CategoriaMovimiento.objects.filter(tipo="egreso", activo=True).order_by("nombre")
    
    CFG = get_config()
    
    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,
        
        # Filtros actuales
        "estado": estado,
        "proveedor_id": proveedor_id,
        "categoria_id": categoria_id,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        
        # Datos
        "items": items,
        "total_monto": total_monto,
        "total_pagado": total_pagado,
        "total_pendiente": total_pendiente,
        "cantidad": cantidad,
        "resumen_estados": resumen_estados,
        
        # Listas para selects
        "proveedores": proveedores,
        "categorias": categorias,
        "ESTADOS": CuentaPorPagar.ESTADO_CHOICES,
    }
    return render(request, "finanzas_app/reportes/reporte_cxp.html", context)


# ----------------------------------------------------------
# REPORTE: CxP POR PROVEEDOR
# ----------------------------------------------------------
@login_required
def reporte_cxp_por_proveedor(request):
    """
    Reporte de CxP agrupado por proveedor.
    Muestra deuda total, pagado y pendiente por cada proveedor.
    Filtros:
      - solo_con_saldo=1 (solo proveedores con saldo pendiente)
      - fecha_desde, fecha_hasta
      - print=1
    """
    hoy = timezone.now().date()
    
    solo_con_saldo = request.GET.get("solo_con_saldo") in ("1", "true", "True", "on")
    fecha_desde = (request.GET.get("fecha_desde") or "").strip()
    fecha_hasta = (request.GET.get("fecha_hasta") or "").strip()
    auto_print = request.GET.get("print") in ("1", "true", "True")
    
    # QuerySet base - excluir canceladas
    qs = CuentaPorPagar.objects.exclude(estado="cancelada")
    
    if fecha_desde:
        qs = qs.filter(fecha_emision__gte=fecha_desde)
    
    if fecha_hasta:
        qs = qs.filter(fecha_emision__lte=fecha_hasta)
    
    # Agrupar por proveedor
    filas = (
        qs.values("proveedor_id", "proveedor__nombre")
        .annotate(
            cantidad=Count("id"),
            monto_total=Sum("monto_total"),
            monto_pagado=Sum("monto_pagado"),
        )
        .order_by("proveedor__nombre")
    )
    
    data = []
    total_monto = Decimal("0")
    total_pagado = Decimal("0")
    
    for f in filas:
        monto = f["monto_total"] or Decimal("0")
        pagado = f["monto_pagado"] or Decimal("0")
        pendiente = monto - pagado
        
        # Si solo_con_saldo, omitir proveedores sin pendiente
        if solo_con_saldo and pendiente <= 0:
            continue
        
        total_monto += monto
        total_pagado += pagado
        
        data.append({
            "proveedor_id": f["proveedor_id"],
            "proveedor": f["proveedor__nombre"] or "Sin proveedor",
            "cantidad": f["cantidad"],
            "monto_total": monto,
            "monto_pagado": pagado,
            "saldo_pendiente": pendiente,
        })
    
    total_pendiente = total_monto - total_pagado
    
    CFG = get_config()
    
    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,
        
        # Filtros
        "solo_con_saldo": solo_con_saldo,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        
        # Datos
        "data": data,
        "total_monto": total_monto,
        "total_pagado": total_pagado,
        "total_pendiente": total_pendiente,
    }
    return render(request, "finanzas_app/reportes/reporte_cxp_por_proveedor.html", context)


# ----------------------------------------------------------
# REPORTE: CxP VENCIDAS Y PRÓXIMAS A VENCER
# ----------------------------------------------------------
@login_required
def reporte_cxp_vencidas(request):
    """
    Reporte de CxP vencidas y próximas a vencer.
    Filtros:
      - dias_alerta (default 7): días para considerar "próxima a vencer"
      - incluir_proximas=1: incluir próximas a vencer
      - proveedor
      - print=1
    """
    hoy = timezone.now().date()
    
    dias_alerta = request.GET.get("dias_alerta", "7")
    incluir_proximas = request.GET.get("incluir_proximas") in ("1", "true", "True", "on")
    proveedor_id = (request.GET.get("proveedor") or "").strip()
    auto_print = request.GET.get("print") in ("1", "true", "True")
    
    try:
        dias_alerta = int(dias_alerta)
        if dias_alerta < 1:
            dias_alerta = 7
    except:
        dias_alerta = 7
    
    fecha_limite = hoy + datetime.timedelta(days=dias_alerta)
    
    # CxP vencidas (fecha_vencimiento < hoy y no pagadas/canceladas)
    qs_vencidas = CuentaPorPagar.objects.filter(
        fecha_vencimiento__lt=hoy
    ).exclude(
        estado__in=["pagada", "cancelada"]
    ).select_related("proveedor", "categoria")
    
    # CxP próximas a vencer
    qs_proximas = CuentaPorPagar.objects.filter(
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=fecha_limite
    ).exclude(
        estado__in=["pagada", "cancelada"]
    ).select_related("proveedor", "categoria")
    
    if proveedor_id:
        qs_vencidas = qs_vencidas.filter(proveedor_id=proveedor_id)
        qs_proximas = qs_proximas.filter(proveedor_id=proveedor_id)
    
    # Procesar vencidas
    vencidas = []
    total_vencidas_monto = Decimal("0")
    total_vencidas_pendiente = Decimal("0")
    
    for item in qs_vencidas.order_by("fecha_vencimiento"):
        dias_mora = (hoy - item.fecha_vencimiento).days
        pendiente = item.saldo_pendiente
        
        total_vencidas_monto += item.monto_total
        total_vencidas_pendiente += pendiente
        
        vencidas.append({
            "obj": item,
            "dias_mora": dias_mora,
            "saldo_pendiente": pendiente,
        })
    
    # Procesar próximas a vencer
    proximas = []
    total_proximas_monto = Decimal("0")
    total_proximas_pendiente = Decimal("0")
    
    if incluir_proximas:
        for item in qs_proximas.order_by("fecha_vencimiento"):
            dias_para_vencer = (item.fecha_vencimiento - hoy).days
            pendiente = item.saldo_pendiente
            
            total_proximas_monto += item.monto_total
            total_proximas_pendiente += pendiente
            
            proximas.append({
                "obj": item,
                "dias_para_vencer": dias_para_vencer,
                "saldo_pendiente": pendiente,
            })
    
    proveedores = ProveedorFinanciero.objects.filter(activo=True).order_by("nombre")
    CFG = get_config()
    
    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,
        
        # Filtros
        "dias_alerta": dias_alerta,
        "incluir_proximas": incluir_proximas,
        "proveedor_id": proveedor_id,
        
        # Datos vencidas
        "vencidas": vencidas,
        "total_vencidas": len(vencidas),
        "total_vencidas_monto": total_vencidas_monto,
        "total_vencidas_pendiente": total_vencidas_pendiente,
        
        # Datos próximas
        "proximas": proximas,
        "total_proximas": len(proximas),
        "total_proximas_monto": total_proximas_monto,
        "total_proximas_pendiente": total_proximas_pendiente,
        
        # Selects
        "proveedores": proveedores,
    }
    return render(request, "finanzas_app/reportes/reporte_cxp_vencidas.html", context)


# ----------------------------------------------------------
# REPORTE: ANTIGÜEDAD DE SALDOS (AGING)
# ----------------------------------------------------------
@login_required
def reporte_antiguedad_cxp(request):
    """
    Reporte de antigüedad de saldos de CxP.
    Clasifica por rangos: 0-30, 31-60, 61-90, +90 días.
    Filtros:
      - proveedor
      - print=1
    """
    hoy = timezone.now().date()
    
    proveedor_id = (request.GET.get("proveedor") or "").strip()
    auto_print = request.GET.get("print") in ("1", "true", "True")
    
    # CxP con saldo pendiente (no pagadas ni canceladas)
    qs = CuentaPorPagar.objects.exclude(
        estado__in=["pagada", "cancelada"]
    ).select_related("proveedor", "categoria")
    
    if proveedor_id:
        qs = qs.filter(proveedor_id=proveedor_id)
    
    # Rangos de antigüedad (días desde fecha_vencimiento o fecha_emision)
    rangos = {
        "corriente": {"label": "Corriente (no vencido)", "min": None, "max": 0, "items": [], "total": Decimal("0")},
        "0_30": {"label": "1-30 días", "min": 1, "max": 30, "items": [], "total": Decimal("0")},
        "31_60": {"label": "31-60 días", "min": 31, "max": 60, "items": [], "total": Decimal("0")},
        "61_90": {"label": "61-90 días", "min": 61, "max": 90, "items": [], "total": Decimal("0")},
        "mas_90": {"label": "Más de 90 días", "min": 91, "max": None, "items": [], "total": Decimal("0")},
    }
    
    total_general = Decimal("0")
    
    for item in qs:
        pendiente = item.saldo_pendiente
        if pendiente <= 0:
            continue
        
        # Calcular días de mora basado en fecha_vencimiento
        fecha_ref = item.fecha_vencimiento or item.fecha_emision
        dias = (hoy - fecha_ref).days if fecha_ref else 0
        
        total_general += pendiente
        
        # Clasificar en rango
        if dias <= 0:
            rangos["corriente"]["items"].append(item)
            rangos["corriente"]["total"] += pendiente
        elif dias <= 30:
            rangos["0_30"]["items"].append(item)
            rangos["0_30"]["total"] += pendiente
        elif dias <= 60:
            rangos["31_60"]["items"].append(item)
            rangos["31_60"]["total"] += pendiente
        elif dias <= 90:
            rangos["61_90"]["items"].append(item)
            rangos["61_90"]["total"] += pendiente
        else:
            rangos["mas_90"]["items"].append(item)
            rangos["mas_90"]["total"] += pendiente
    
    # Calcular porcentajes
    for key in rangos:
        if total_general > 0:
            rangos[key]["porcentaje"] = (rangos[key]["total"] / total_general * 100)
        else:
            rangos[key]["porcentaje"] = Decimal("0")
        rangos[key]["cantidad"] = len(rangos[key]["items"])
    
    # Resumen por proveedor con aging
    proveedores_aging = defaultdict(lambda: {
        "nombre": "",
        "corriente": Decimal("0"),
        "0_30": Decimal("0"),
        "31_60": Decimal("0"),
        "61_90": Decimal("0"),
        "mas_90": Decimal("0"),
        "total": Decimal("0"),
    })
    
    for item in qs:
        pendiente = item.saldo_pendiente
        if pendiente <= 0:
            continue
        
        prov_id = item.proveedor_id
        prov_nombre = item.proveedor.nombre if item.proveedor else "Sin proveedor"
        
        proveedores_aging[prov_id]["nombre"] = prov_nombre
        proveedores_aging[prov_id]["total"] += pendiente
        
        fecha_ref = item.fecha_vencimiento or item.fecha_emision
        dias = (hoy - fecha_ref).days if fecha_ref else 0
        
        if dias <= 0:
            proveedores_aging[prov_id]["corriente"] += pendiente
        elif dias <= 30:
            proveedores_aging[prov_id]["0_30"] += pendiente
        elif dias <= 60:
            proveedores_aging[prov_id]["31_60"] += pendiente
        elif dias <= 90:
            proveedores_aging[prov_id]["61_90"] += pendiente
        else:
            proveedores_aging[prov_id]["mas_90"] += pendiente
    
    # Convertir a lista ordenada
    proveedores_lista = sorted(
        proveedores_aging.values(),
        key=lambda x: x["total"],
        reverse=True
    )
    
    proveedores = ProveedorFinanciero.objects.filter(activo=True).order_by("nombre")
    CFG = get_config()
    
    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,
        
        # Filtros
        "proveedor_id": proveedor_id,
        
        # Datos
        "rangos": rangos,
        "total_general": total_general,
        "proveedores_aging": proveedores_lista,
        
        # Selects
        "proveedores": proveedores,
    }
    return render(request, "finanzas_app/reportes/reporte_antiguedad_cxp.html", context)


# ----------------------------------------------------------
# REPORTE: HISTORIAL DE PAGOS DE CxP
# ----------------------------------------------------------
@login_required
def reporte_pagos_cxp(request):
    """
    Reporte de pagos realizados a CxP en un período.
    Filtros:
      - year, month
      - proveedor
      - print=1
    """
    from .models import MovimientoFinanciero
    
    hoy = timezone.now().date()
    
    year = request.GET.get("year")
    month = request.GET.get("month")
    proveedor_id = (request.GET.get("proveedor") or "").strip()
    auto_print = request.GET.get("print") in ("1", "true", "True")
    
    try:
        year = int(year) if year else hoy.year
        month = int(month) if month else hoy.month
        if month < 1 or month > 12:
            raise ValueError
    except:
        year = hoy.year
        month = hoy.month
    
    # Pagos vinculados a CxP (movimientos con cuenta_por_pagar)
    qs = MovimientoFinanciero.objects.filter(
        cuenta_por_pagar__isnull=False,
        fecha__year=year,
        fecha__month=month,
        tipo="egreso",
    ).exclude(estado="anulado").select_related(
        "cuenta", "cuenta_por_pagar", "cuenta_por_pagar__proveedor", "creado_por"
    )
    
    if proveedor_id:
        qs = qs.filter(cuenta_por_pagar__proveedor_id=proveedor_id)
    
    qs = qs.order_by("-fecha", "-creado_en")
    
    # Totales
    totales = qs.aggregate(
        total_pagado=Sum("monto"),
        cantidad=Count("id"),
    )
    
    total_pagado = totales.get("total_pagado") or Decimal("0")
    cantidad = totales.get("cantidad") or 0
    
    # Resumen por proveedor
    por_proveedor = (
        qs.values("cuenta_por_pagar__proveedor__nombre")
        .annotate(
            monto=Sum("monto"),
            cantidad=Count("id"),
        )
        .order_by("-monto")
    )
    
    NOMBRES_MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    mes_label = f"{NOMBRES_MESES[month]} {year}"
    
    proveedores = ProveedorFinanciero.objects.filter(activo=True).order_by("nombre")
    CFG = get_config()
    
    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,
        
        # Filtros
        "year": year,
        "month": month,
        "mes_label": mes_label,
        "proveedor_id": proveedor_id,
        "meses": [(i, NOMBRES_MESES[i]) for i in range(1, 13)],
        
        # Datos
        "items": qs,
        "total_pagado": total_pagado,
        "cantidad": cantidad,
        "por_proveedor": por_proveedor,
        
        # Selects
        "proveedores": proveedores,
    }
    return render(request, "finanzas_app/reportes/reporte_pagos_cxp.html", context)


# ============================================
# AGREGAR ESTA VISTA A finanzas_app/views.py
# ============================================

# ============================================
# AGREGAR ESTA VISTA A finanzas_app/views.py
# ============================================

@login_required
def reporte_estado_resultados(request):
    """
    Estado de Resultados (Ingresos vs Egresos).
    Muestra todas las cuentas consolidadas (sin filtro de cuenta).
    Filtros:
      - year, month (por defecto mes actual)
      - print=1 (opcional)
    """
    hoy = timezone.now().date()

    # ---- Filtros ----
    year = request.GET.get("year")
    month = request.GET.get("month")
    auto_print = request.GET.get("print") in ("1", "true", "True")

    try:
        year = int(year) if year else hoy.year
        month = int(month) if month else hoy.month
        if month < 1 or month > 12:
            raise ValueError
    except Exception:
        year = hoy.year
        month = hoy.month

    # ---- Query base (todas las cuentas consolidadas) ----
    qs = MovimientoFinanciero.objects.filter(
        fecha__year=year,
        fecha__month=month,
    ).exclude(
        estado="anulado"
    ).exclude(
        es_transferencia=True  # Las transferencias no son ingresos/egresos reales
    )

    # ---- INGRESOS por categoría ----
    ingresos_por_categoria = (
        qs.filter(tipo="ingreso")
        .values("categoria__nombre")
        .annotate(total=Sum("monto"))
        .order_by("-total")
    )

    ingresos_detalle = []
    total_ingresos = Decimal("0")
    for row in ingresos_por_categoria:
        monto = row["total"] or Decimal("0")
        total_ingresos += monto
        ingresos_detalle.append({
            "categoria": row["categoria__nombre"] or "Sin categoría",
            "monto": monto,
        })

    # ---- EGRESOS por categoría ----
    egresos_por_categoria = (
        qs.filter(tipo="egreso")
        .values("categoria__nombre")
        .annotate(total=Sum("monto"))
        .order_by("-total")
    )

    egresos_detalle = []
    total_egresos = Decimal("0")
    for row in egresos_por_categoria:
        monto = row["total"] or Decimal("0")
        total_egresos += monto
        egresos_detalle.append({
            "categoria": row["categoria__nombre"] or "Sin categoría",
            "monto": monto,
        })

    # ---- RESULTADO ----
    resultado = total_ingresos - total_egresos
    es_superavit = resultado >= 0

    # ---- Período label ----
    NOMBRES_MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    periodo_label = f"{NOMBRES_MESES[month]} {year}"

    CFG = get_config()

    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,

        # Filtros
        "year": year,
        "month": month,
        "periodo_label": periodo_label,
        "meses": [(i, NOMBRES_MESES[i]) for i in range(1, 13)],

        # Datos de ingresos
        "ingresos_detalle": ingresos_detalle,
        "total_ingresos": total_ingresos,

        # Datos de egresos
        "egresos_detalle": egresos_detalle,
        "total_egresos": total_egresos,

        # Resultado
        "resultado": resultado,
        "es_superavit": es_superavit,
    }
    return render(request, "finanzas_app/reportes/estado_resultados.html", context)

# ============================================
# AGREGAR ESTAS VISTAS A finanzas_app/views.py
# ============================================

# ============================================
# AGREGAR ESTAS VISTAS A finanzas_app/views.py
# ============================================

@login_required
def reporte_ingresos_por_unidad(request):
    """
    Reporte de ingresos (MovimientoFinanciero) agrupados por unidad.
    Muestra qué unidades generan ingresos para la iglesia.
    Filtros:
      - year, month
      - unidad (opcional)
      - print=1
    """
    from estructura_app.models import Unidad
    
    hoy = timezone.now().date()

    # ---- Filtros ----
    year = request.GET.get("year")
    month = request.GET.get("month")
    unidad_id = (request.GET.get("unidad") or "").strip()
    auto_print = request.GET.get("print") in ("1", "true", "True")

    try:
        year = int(year) if year else hoy.year
        month = int(month) if month else hoy.month
        if month < 1 or month > 12:
            raise ValueError
    except Exception:
        year = hoy.year
        month = hoy.month

    # ---- Query base: solo ingresos ----
    qs = MovimientoFinanciero.objects.filter(
        fecha__year=year,
        fecha__month=month,
        tipo="ingreso",
    ).exclude(
        estado="anulado"
    ).exclude(
        es_transferencia=True
    ).select_related("unidad", "categoria")

    if unidad_id:
        qs = qs.filter(unidad_id=unidad_id)

    # ---- Agrupar por unidad ----
    from django.db.models import Sum, Count

    # Ingresos CON unidad asignada
    ingresos_por_unidad = (
        qs.filter(unidad__isnull=False)
        .values("unidad__id", "unidad__nombre")
        .annotate(
            total=Sum("monto"),
            cantidad=Count("id")
        )
        .order_by("-total")
    )

    # Detalle por unidad y categoría
    detalle_unidades = []
    total_con_unidad = Decimal("0")

    for item in ingresos_por_unidad:
        unidad_data = {
            "id": item["unidad__id"],
            "nombre": item["unidad__nombre"],
            "total": item["total"] or Decimal("0"),
            "cantidad": item["cantidad"],
            "categorias": []
        }
        total_con_unidad += unidad_data["total"]

        # Detalle por categoría de esta unidad
        categorias = (
            qs.filter(unidad_id=item["unidad__id"])
            .values("categoria__nombre")
            .annotate(subtotal=Sum("monto"))
            .order_by("-subtotal")
        )
        for cat in categorias:
            unidad_data["categorias"].append({
                "nombre": cat["categoria__nombre"] or "Sin categoría",
                "monto": cat["subtotal"] or Decimal("0"),
            })

        detalle_unidades.append(unidad_data)

    # Total general (solo los que tienen unidad)
    total_general = total_con_unidad

    # ---- Período label ----
    NOMBRES_MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    periodo_label = f"{NOMBRES_MESES[month]} {year}"

    # ---- Combos ----
    unidades = Unidad.objects.filter(activa=True, visible=True).order_by("nombre")
    CFG = get_config()

    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,

        # Filtros
        "year": year,
        "month": month,
        "periodo_label": periodo_label,
        "meses": [(i, NOMBRES_MESES[i]) for i in range(1, 13)],
        "unidad_id": unidad_id,
        "unidades": unidades,

        # Datos
        "detalle_unidades": detalle_unidades,
        "total_general": total_general,
    }
    return render(request, "finanzas_app/reportes/ingresos_por_unidad.html", context)

# ============================================
# AGREGAR ESTA VISTA A estructura_app/views.py
# (o finanzas_app/views.py si prefieres centralizar)
# ============================================

@login_required
def reporte_movimientos_unidad(request):
    """
    Reporte de movimientos internos de unidades (MovimientoUnidad).
    Muestra ingresos y egresos del fondo propio de cada unidad.
    Filtros:
      - year, month
      - unidad (opcional)
      - print=1
    """
    from estructura_app.models import Unidad, MovimientoUnidad
    from django.db.models import Sum, Count, Q
    
    hoy = timezone.now().date()

    # ---- Filtros ----
    year = request.GET.get("year")
    month = request.GET.get("month")
    unidad_id = (request.GET.get("unidad") or "").strip()
    auto_print = request.GET.get("print") in ("1", "true", "True")

    try:
        year = int(year) if year else hoy.year
        month = int(month) if month else hoy.month
        if month < 1 or month > 12:
            raise ValueError
    except Exception:
        year = hoy.year
        month = hoy.month

    # ---- Query base ----
    qs = MovimientoUnidad.objects.filter(
        fecha__year=year,
        fecha__month=month,
        anulado=False,
    ).select_related("unidad")

    if unidad_id:
        qs = qs.filter(unidad_id=unidad_id)

    # ---- Agrupar por unidad ----
    resumen_por_unidad = (
        qs.values("unidad__id", "unidad__nombre")
        .annotate(
            ingresos=Sum("monto", filter=Q(tipo="INGRESO")),
            egresos=Sum("monto", filter=Q(tipo="EGRESO")),
            cantidad=Count("id"),
        )
        .order_by("unidad__nombre")
    )

    # Construir detalle
    detalle_unidades = []
    total_ingresos = Decimal("0")
    total_egresos = Decimal("0")

    for item in resumen_por_unidad:
        ing = item["ingresos"] or Decimal("0")
        egr = item["egresos"] or Decimal("0")
        resultado = ing - egr

        total_ingresos += ing
        total_egresos += egr

        # Obtener movimientos detallados de esta unidad
        movimientos = qs.filter(unidad_id=item["unidad__id"]).order_by("fecha", "id")

        detalle_unidades.append({
            "id": item["unidad__id"],
            "nombre": item["unidad__nombre"],
            "ingresos": ing,
            "egresos": egr,
            "resultado": resultado,
            "cantidad": item["cantidad"],
            "movimientos": movimientos,
        })

    total_resultado = total_ingresos - total_egresos

    # ---- Período label ----
    NOMBRES_MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    periodo_label = f"{NOMBRES_MESES[month]} {year}"

    # ---- Combos ----
    unidades = Unidad.objects.filter(activa=True, visible=True).order_by("nombre")
    CFG = get_config()

    context = {
        "CFG": CFG,
        "fecha_hoy": hoy,
        "auto_print": auto_print,

        # Filtros
        "year": year,
        "month": month,
        "periodo_label": periodo_label,
        "meses": [(i, NOMBRES_MESES[i]) for i in range(1, 13)],
        "unidad_id": unidad_id,
        "unidades": unidades,

        # Datos
        "detalle_unidades": detalle_unidades,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "total_resultado": total_resultado,
    }
    return render(request, "finanzas_app/reportes/movimientos_unidad.html", context)