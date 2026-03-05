# finanzas_app/views/cxp.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET, require_http_methods
from django.db.models import Sum, Q
from django.db import transaction
from decimal import Decimal
import datetime

from ..models import (
    MovimientoFinanciero,
    CuentaFinanciera,
    CategoriaMovimiento,
    ProveedorFinanciero,
    CuentaPorPagar,
)
from ..forms import CuentaPorPagarForm


@login_required
@require_GET
@permission_required("finanzas_app.view_cuentaporpagar", raise_exception=True)
def cxp_list(request):
    """
    Listado de Cuentas por Pagar con filtros.
    """
    tenant = request.tenant  # 👈 TENANT
    
    estado = (request.GET.get("estado") or "").strip()
    q = (request.GET.get("q") or "").strip()
    proveedor_id = (request.GET.get("proveedor") or "").strip()
    fecha_desde = (request.GET.get("fecha_desde") or "").strip()
    fecha_hasta = (request.GET.get("fecha_hasta") or "").strip()

    qs = CuentaPorPagar.objects.filter(
        tenant=tenant  # 👈 FILTRAR POR TENANT
    ).select_related(
        "proveedor", "categoria", "cuenta_sugerida"
    )

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
    proveedores = ProveedorFinanciero.objects.filter(tenant=tenant, activo=True).order_by("nombre")  # 👈 FILTRAR POR TENANT

    # Agregar propiedades de vencimiento
    hoy = datetime.date.today()
    items_con_vencimiento = []
    for item in qs:
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
    """
    Crear una nueva Cuenta por Pagar.
    """
    tenant = request.tenant  # 👈 TENANT
    
    if request.method == "POST":
        form = CuentaPorPagarForm(request.POST, tenant=tenant)  # 👈 PASAR TENANT
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant = tenant  # 👈 ASIGNAR TENANT
            obj.creado_por = request.user
            obj.estado = "pendiente"
            obj.monto_pagado = obj.monto_pagado or 0
            obj.save()

            messages.success(request, "✅ Cuenta por pagar creada correctamente.")
            return redirect("finanzas_app:cxp_detail", pk=obj.pk)
    else:
        form = CuentaPorPagarForm(tenant=tenant)  # 👈 PASAR TENANT

    return render(request, "finanzas_app/cxp/crear.html", {"form": form})


@login_required
@require_GET
@permission_required("finanzas_app.view_cuentaporpagar", raise_exception=True)
def cxp_detail(request, pk):
    """
    Detalle de una Cuenta por Pagar.
    """
    tenant = request.tenant  # 👈 TENANT
    
    obj = get_object_or_404(
        CuentaPorPagar.objects.select_related(
            "proveedor", "categoria", "cuenta_sugerida"
        ),
        pk=pk,
        tenant=tenant  # 👈 FILTRAR POR TENANT
    )

    # Obtener historial de pagos vinculados
    pagos = MovimientoFinanciero.objects.filter(
        tenant=tenant,  # 👈 FILTRAR POR TENANT
        cuenta_por_pagar=obj
    ).select_related("cuenta", "creado_por").order_by("-fecha", "-creado_en")

    return render(request, "finanzas_app/cxp/detalle.html", {
        "obj": obj,
        "pagos": pagos,
    })


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.change_cuentaporpagar", raise_exception=True)
def cxp_edit(request, pk):
    """
    Editar una Cuenta por Pagar existente.
    """
    tenant = request.tenant  # 👈 TENANT
    cxp = get_object_or_404(CuentaPorPagar, pk=pk, tenant=tenant)  # 👈 FILTRAR POR TENANT

    if cxp.estado == "pagada":
        messages.warning(request, "Esta cuenta ya está pagada y no puede ser modificada.")
        return redirect("finanzas_app:cxp_detail", pk=cxp.pk)

    if request.method == "POST":
        form = CuentaPorPagarForm(request.POST, instance=cxp, tenant=tenant)  # 👈 PASAR TENANT
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta por pagar actualizada correctamente.")
            return redirect("finanzas_app:cxp_detail", pk=cxp.pk)
    else:
        form = CuentaPorPagarForm(instance=cxp, tenant=tenant)  # 👈 PASAR TENANT

    context = {
        "form": form,
        "obj": cxp,
        "modo": "editar",
    }

    return render(request, "finanzas_app/cxp_form.html", context)


@login_required
@transaction.atomic
def cxp_pagar(request, pk):
    """
    Registrar un pago (total o parcial) a una Cuenta por Pagar.
    """
    tenant = request.tenant  # 👈 TENANT
    cxp = get_object_or_404(CuentaPorPagar, pk=pk, tenant=tenant)  # 👈 FILTRAR POR TENANT

    if cxp.estado in ("pagada", "cancelada"):
        messages.warning(request, "Esta cuenta ya está pagada o cancelada.")
        return redirect("finanzas_app:cxp_detail", pk=cxp.pk)

    cuentas = CuentaFinanciera.objects.filter(tenant=tenant, esta_activa=True).order_by("nombre")  # 👈 FILTRAR POR TENANT

    if request.method == "POST":
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
            cuenta = CuentaFinanciera.objects.get(pk=cuenta_id, tenant=tenant, esta_activa=True)  # 👈 FILTRAR POR TENANT
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
                tenant=tenant,  # 👈 ASIGNAR TENANT
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
                cuenta_por_pagar=cxp,
            )

            # Actualizar la CxP
            cxp.monto_pagado = (cxp.monto_pagado or Decimal("0")) + monto

            if cxp.monto_pagado >= cxp.monto_total:
                cxp.estado = "pagada"
            else:
                cxp.estado = "parcial"

            cxp.save()

            messages.success(request, f"✅ Pago de RD$ {monto:,.2f} registrado correctamente.")
            return redirect("finanzas_app:cxp_detail", pk=cxp.pk)

    fecha_hoy = datetime.date.today()

    context = {
        "cxp": cxp,
        "cuentas": cuentas,
        "fecha_hoy": fecha_hoy,
        "FORMA_PAGO_CHOICES": MovimientoFinanciero.FORMA_PAGO_CHOICES,
    }

    return render(request, "finanzas_app/cxp/pagar.html", context)