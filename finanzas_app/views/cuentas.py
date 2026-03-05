# finanzas_app/views/cuentas.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db.models import Sum, Q
from decimal import Decimal

from ..models import (
    MovimientoFinanciero,
    CuentaFinanciera,
)
from ..forms import CuentaFinancieraForm


@login_required
@require_GET
@permission_required("finanzas_app.view_cuentafinanciera", raise_exception=True)
def cuentas_listado(request):
    """
    Listado de todas las cuentas financieras con saldo actual calculado.
    """
    tenant = request.tenant  # 👈 TENANT
    
    cuentas = CuentaFinanciera.objects.filter(
        tenant=tenant  # 👈 FILTRAR POR TENANT
    ).order_by("-esta_activa", "nombre")

    total_activas = cuentas.filter(esta_activa=True).count()
    total_inactivas = cuentas.filter(esta_activa=False).count()

    # Calcular saldo actual para cada cuenta
    cuentas_con_saldo = []
    saldo_total_general = Decimal("0")

    for cuenta in cuentas:
        # Obtener totales de movimientos de esta cuenta (excluyendo anulados)
        totales = MovimientoFinanciero.objects.filter(
            tenant=tenant,  # 👈 FILTRAR POR TENANT
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
    tenant = request.tenant  # 👈 TENANT
    
    if request.method == "POST":
        form = CuentaFinancieraForm(request.POST, tenant=tenant)  # 👈 PASAR TENANT
        if form.is_valid():
            cuenta = form.save(commit=False)
            cuenta.tenant = tenant  # 👈 ASIGNAR TENANT
            cuenta.save()
            messages.success(request, f"Cuenta «{cuenta.nombre}» creada correctamente.")
            return redirect("finanzas_app:cuentas_listado")
    else:
        form = CuentaFinancieraForm(tenant=tenant)  # 👈 PASAR TENANT

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
    tenant = request.tenant  # 👈 TENANT
    cuenta = get_object_or_404(CuentaFinanciera, pk=pk, tenant=tenant)  # 👈 FILTRAR POR TENANT

    if request.method == "POST":
        form = CuentaFinancieraForm(request.POST, instance=cuenta, tenant=tenant)  # 👈 PASAR TENANT
        if form.is_valid():
            form.save()
            messages.success(request, f"Cuenta «{cuenta.nombre}» actualizada correctamente.")
            return redirect("finanzas_app:cuentas_listado")
    else:
        form = CuentaFinancieraForm(instance=cuenta, tenant=tenant)  # 👈 PASAR TENANT

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
    tenant = request.tenant  # 👈 TENANT
    cuenta = get_object_or_404(CuentaFinanciera, pk=pk, tenant=tenant)  # 👈 FILTRAR POR TENANT

    # Toggle del estado
    cuenta.esta_activa = not cuenta.esta_activa
    cuenta.save()

    if cuenta.esta_activa:
        messages.success(request, f"Cuenta «{cuenta.nombre}» activada.")
    else:
        messages.warning(request, f"Cuenta «{cuenta.nombre}» desactivada.")

    return redirect("finanzas_app:cuentas_listado")