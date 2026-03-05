# finanzas_app/views/transferencias.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Sum, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import json

from core.utils_config import get_config

from ..models import (
    MovimientoFinanciero,
    CuentaFinanciera,
)
from ..forms import TransferenciaForm
from ..services import TransferenciaService


@login_required
@permission_required("finanzas_app.add_transferencia", raise_exception=True)
def transferencia_crear(request):
    """
    Vista para crear una transferencia entre cuentas.
    Incluye saldos de cuentas para validación visual.
    """
    tenant = request.tenant  # 👈 TENANT

    # CALCULAR SALDOS DE TODAS LAS CUENTAS ACTIVAS
    cuentas_con_saldo = {}

    for cuenta in CuentaFinanciera.objects.filter(tenant=tenant, esta_activa=True):  # 👈 FILTRAR POR TENANT
        movs = MovimientoFinanciero.objects.filter(
            tenant=tenant,  # 👈 FILTRAR POR TENANT
            cuenta=cuenta
        ).exclude(estado="anulado").aggregate(
            ingresos=Sum("monto", filter=Q(tipo="ingreso")),
            egresos=Sum("monto", filter=Q(tipo="egreso")),
        )
        ing = movs.get("ingresos") or Decimal("0")
        egr = movs.get("egresos") or Decimal("0")
        saldo = cuenta.saldo_inicial + ing - egr
        cuentas_con_saldo[cuenta.id] = {
            "saldo": float(saldo),
            "nombre": cuenta.nombre,
            "moneda": cuenta.moneda,
        }

    if request.method == "POST":
        form = TransferenciaForm(request.POST, tenant=tenant)  # 👈 PASAR TENANT
        if form.is_valid():
            try:
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
                    validar_saldo=True,
                    tenant=tenant  # 👈 PASAR TENANT AL SERVICIO
                )

                messages.success(
                    request,
                    f"Transferencia de {cuenta_origen.moneda} {monto:,.2f} realizada exitosamente. "
                    f"De '{cuenta_origen.nombre}' a '{cuenta_destino.nombre}'."
                )
                return redirect("finanzas_app:transferencia_detalle", pk=mov_envio.pk)

            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = TransferenciaForm(initial={"fecha": timezone.now().date()}, tenant=tenant)  # 👈 PASAR TENANT

    context = {
        "form": form,
        "cuentas_saldos_json": json.dumps(cuentas_con_saldo),
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
    tenant = request.tenant  # 👈 TENANT
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk, tenant=tenant)  # 👈 FILTRAR POR TENANT

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
    """
    tenant = request.tenant  # 👈 TENANT
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk, tenant=tenant)  # 👈 FILTRAR POR TENANT

    if not movimiento.es_transferencia:
        messages.error(request, "Este movimiento no es una transferencia.")
        return redirect("finanzas_app:movimientos_listado")

    movimiento_par = movimiento.get_transferencia_par()
    if not movimiento_par:
        messages.error(request, "No se encontró el movimiento vinculado de esta transferencia.")
        return redirect("finanzas_app:movimientos_listado")

    if movimiento.tipo == "egreso":
        mov_envio = movimiento
        mov_recepcion = movimiento_par
    else:
        mov_envio = movimiento_par
        mov_recepcion = movimiento

    if mov_envio.estado == "anulado" or mov_recepcion.estado == "anulado":
        messages.warning(request, "Esta transferencia ya está anulada.")
        return redirect("finanzas_app:transferencia_detalle", pk=mov_envio.pk)

    back_url = redirect("finanzas_app:transferencia_detalle", pk=mov_envio.pk).url

    if request.method == "POST":
        motivo = (request.POST.get("motivo") or "").strip()

        if not motivo:
            messages.error(request, "Debes indicar el motivo de la anulación.")
        else:
            for mov in (mov_envio, mov_recepcion):
                mov.estado = "anulado"
                if hasattr(mov, "motivo_anulacion"):
                    mov.motivo_anulacion = motivo
                if hasattr(mov, "anulado_por"):
                    mov.anulado_por = request.user
                if hasattr(mov, "anulado_en"):
                    mov.anulado_en = timezone.now()
                mov.save()

            messages.success(request, "Transferencia anulada correctamente.")
            return redirect("finanzas_app:transferencia_detalle", pk=mov_envio.pk)

    context = {
        "modo": "transferencia",
        "transferencia": mov_envio,
        "cuenta_origen": mov_envio.cuenta.nombre,
        "cuenta_destino": mov_recepcion.cuenta.nombre,
        "back_url": back_url,
    }
    return render(request, "finanzas_app/anulacion_confirmar.html", context)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def transferencia_general_pdf(request, pk):
    """
    Vista para generar PDF de transferencia.
    """
    tenant = request.tenant  # 👈 TENANT
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk, tenant=tenant, es_transferencia=True)  # 👈 FILTRAR POR TENANT
    
    movimiento_par = movimiento.get_transferencia_par()
    
    if movimiento.tipo == "egreso":
        mov_envio = movimiento
        mov_recepcion = movimiento_par
    else:
        mov_envio = movimiento_par
        mov_recepcion = movimiento
    
    CFG = get_config()

    context = {
        "CFG": CFG,
        "transferencia": movimiento,
        "mov_envio": mov_envio,
        "mov_recepcion": mov_recepcion,
        "auto_print": False,
    }
    return render(request, "finanzas_app/recibos/transferencia_general.html", context)