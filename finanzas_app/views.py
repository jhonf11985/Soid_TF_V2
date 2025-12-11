# finanzas_app/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from decimal import Decimal
import json
import datetime

from .models import MovimientoFinanciero, CuentaFinanciera, CategoriaMovimiento
from .forms import (
    MovimientoFinancieroForm, 
    MovimientoIngresoForm, 
    CuentaFinancieraForm,
    MovimientoEgresoForm, 
    CategoriaMovimientoForm,
)


# ============================================
# DASHBOARD
# ============================================

@login_required
def dashboard(request):
    """
    Dashboard de Finanzas con datos reales.
    """
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
def cuentas_listado(request):
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
def categoria_toggle(request, pk):
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
def movimientos_listado(request):
    """
    Listado de movimientos financieros con filtros básicos y totales.
    """
    movimientos = MovimientoFinanciero.objects.select_related(
        "cuenta", "categoria", "creado_por"
    ).order_by("-fecha", "-creado_en")

    # --------- FILTROS ----------
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
            Q(referencia__icontains=q)
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
def ingreso_crear(request):
    """
    Formulario específico para registrar INGRESOS.
    """
    if request.method == "POST":
        form = MovimientoIngresoForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.tipo = "ingreso"
            mov.creado_por = request.user
            mov.save()
            messages.success(request, "Ingreso registrado correctamente.")
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
def movimiento_editar(request, pk):
    """
    Editar un movimiento financiero existente.
    - Si es ingreso: usa MovimientoIngresoForm + ingreso_form.html
    - Si es egreso: usa MovimientoEgresoForm + egreso.html
    """
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)

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
def movimiento_anular(request, pk):
    """
    Anular un movimiento (cambiar estado a 'anulado').
    No eliminamos para mantener el historial.
    """
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)
    
    movimiento.estado = "anulado"
    movimiento.save()

    messages.warning(request, f"Movimiento #{movimiento.pk} anulado.")
    return redirect("finanzas_app:movimientos_listado")