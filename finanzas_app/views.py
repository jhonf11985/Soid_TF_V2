from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from .models import MovimientoFinanciero, CuentaFinanciera, CategoriaMovimiento
from .forms import MovimientoFinancieroForm, MovimientoIngresoForm
from django.utils import timezone



@login_required
def dashboard(request):
    """
    Dashboard de Finanzas.
    De momento solo renderiza la plantilla estática.
    Más adelante conectaremos aquí los totales reales.
    """
    context = {}
    # IMPORTANTE: usamos finanzas_app/dashboard.html porque así se llama la carpeta
    return render(request, "finanzas_app/dashboard.html", context)


@login_required
def movimientos_listado(request):
    """
    Listado de movimientos financieros con filtros básicos y totales.
    Solo accesible para usuarios autenticados.
    """
    movimientos = MovimientoFinanciero.objects.select_related(
        "cuenta", "categoria", "creado_por"
    ).order_by("-fecha", "-creado_en")

    # --------- FILTROS ----------
    tipo = request.GET.get("tipo")  # ingreso / egreso
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
        # valores de los filtros para mantener el estado en el formulario
        "f_tipo": tipo or "",
        "f_cuenta": cuenta_id or "",
        "f_categoria": categoria_id or "",
        "f_q": q or "",
        "f_fecha_desde": fecha_desde or "",
        "f_fecha_hasta": fecha_hasta or "",
    }
    # OJO: carpeta finanzas_app en templates
    return render(request, "finanzas_app/movimientos_listado.html", context)


@login_required
def movimiento_crear(request):
    """
    Formulario para registrar un nuevo movimiento (ingreso o egreso).
    Solo accesible para usuarios autenticados.
    """
    if request.method == "POST":
        form = MovimientoFinancieroForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            if request.user.is_authenticated:
                mov.creado_por = request.user
            mov.save()
            messages.success(request, "Movimiento registrado correctamente.")
            return redirect("finanzas_app:movimientos_listado")
    else:
        form = MovimientoFinancieroForm()

    context = {
        "form": form,
    }
    # OJO: carpeta finanzas_app en templates
    return render(request, "finanzas_app/movimiento_form.html", context)

@login_required
def ingreso_crear(request):
    """
    Formulario específico para registrar INGRESOS.
    - Fija mov.tipo = 'ingreso'
    - Filtra categorías a solo ingresos (hecho en el form)
    """
    if request.method == "POST":
        form = MovimientoIngresoForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.tipo = "ingreso"  # aseguramos que siempre sea ingreso
            if request.user.is_authenticated:
                mov.creado_por = request.user
            mov.save()
            messages.success(request, "Ingreso registrado correctamente.")
            # Volvemos al listado filtrado por ingresos
            return redirect("/finanzas/movimientos/?tipo=ingreso")
    else:
        form = MovimientoIngresoForm(
            initial={
                "fecha": timezone.now().date(),
            }
        )

    context = {
        "form": form,
    }
    return render(request, "finanzas_app/ingreso_form.html", context)