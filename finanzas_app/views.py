# finanzas_app/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import MovimientoFinanciero, CuentaFinanciera, CategoriaMovimiento
from .forms import (
    MovimientoFinancieroForm, 
    MovimientoIngresoForm, 
    CuentaFinancieraForm,MovimientoEgresoForm, 
    CategoriaMovimientoForm,
)


# ============================================
# DASHBOARD
# ============================================

@login_required
def dashboard(request):
    """
    Dashboard de Finanzas.
    De momento solo renderiza la plantilla estática.
    Más adelante conectaremos aquí los totales reales.
    """
    context = {}
    return render(request, "finanzas_app/dashboard.html", context)


# ============================================
# CUENTAS FINANCIERAS - CRUD
# ============================================

@login_required
def cuentas_listado(request):
    """
    Listado de todas las cuentas financieras.
    """
    cuentas = CuentaFinanciera.objects.all().order_by("-esta_activa", "nombre")
    
    total_activas = cuentas.filter(esta_activa=True).count()
    total_inactivas = cuentas.filter(esta_activa=False).count()

    context = {
        "cuentas": cuentas,
        "total_activas": total_activas,
        "total_inactivas": total_inactivas,
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
from .forms import MovimientoEgresoForm

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

    return render(request, "finanzas_app/egreso.html", {"form": form})
