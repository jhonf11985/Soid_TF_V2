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


from .models import MovimientoFinanciero, CuentaFinanciera, CategoriaMovimiento
from .forms import (
    MovimientoFinancieroForm, 
    MovimientoIngresoForm, 
    CuentaFinancieraForm,
    MovimientoEgresoForm, 
    CategoriaMovimientoForm,
)
from django.db import transaction
from django.utils import timezone

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
    ).exclude(estado="anulado").order_by("-fecha", "-creado_en")

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
def movimiento_anular(request, pk):
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)

    if movimiento.estado == "anulado":
        messages.warning(request, "Este movimiento ya está anulado.")
        return redirect("finanzas_app:movimientos_listado")

    if request.method == "POST":
        motivo = (request.POST.get("motivo") or "").strip()
        if not motivo:
            messages.error(request, "Debes indicar el motivo de la anulación.")
            return redirect("finanzas_app:movimiento_anular", pk=movimiento.pk)

        movimiento.estado = "anulado"
        movimiento.motivo_anulacion = motivo
        movimiento.anulado_por = request.user
        movimiento.anulado_en = timezone.now()
        movimiento.save()

        messages.warning(request, f"Movimiento #{movimiento.pk} anulado.")
        return redirect("finanzas_app:movimientos_listado")

    context = {
        "modo": "movimiento",
        "movimiento": movimiento,
        "back_url": request.META.get("HTTP_REFERER") or reverse("finanzas_app:movimientos_listado"),
    }


    messages.success(
        request,
        f"El {movimiento.tipo} fue anulado correctamente."
    )


    return render(request, "finanzas_app/anulacion_confirmar.html", context)


@login_required
def ingreso_detalle(request, pk):
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
def buscar_miembros_finanzas(request):
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
def subir_adjunto(request, movimiento_id):
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
def descargar_adjunto(request, adjunto_id):
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
def listar_adjuntos(request, movimiento_id):
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
def ingreso_recibo(request, pk):
    """
    Vista SOLO para imprimir el recibo de un ingreso (formato 80mm).
    """
    ingreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="ingreso")

    context = {
        "ingreso": ingreso,
        "auto_print": True,  # para que el template pueda disparar window.print()
    }
    return render(request, "finanzas_app/recibos/ingreso_recibo.html", context)



def ingreso_general_pdf(request, pk):
    ingreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="ingreso")
    CFG = get_config()
    return render(request, "finanzas_app/recibos/ingreso_general_pdf.html", {"ingreso": ingreso, "CFG": CFG})

@login_required
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
def egreso_detalle(request, pk):
    egreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="egreso")
    return render(request, "finanzas_app/egreso_detalle.html", {"egreso": egreso})

@login_required
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
