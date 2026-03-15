from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from estructura_app.forms import MovimientoUnidadForm, MovimientoUnidadEditarForm
from estructura_app.models import Unidad, MovimientoUnidad, MovimientoUnidadLog
from estructura_app.view_helpers.common import _get_client_ip, _require_tenant


@login_required
@permission_required("estructura_app.add_movimientounidad", raise_exception=True)
def unidad_movimiento_crear(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    if request.method == "POST":
        form = MovimientoUnidadForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant = tenant
            obj.unidad = unidad
            obj.creado_por = request.user
            obj.actualizado_por = request.user
            obj.save()

            MovimientoUnidadLog.objects.create(
                tenant=tenant,
                movimiento=obj,
                accion=MovimientoUnidadLog.ACCION_CREAR,
                usuario=request.user,
                fecha_antes=None,
                fecha_despues=obj.fecha,
                concepto_antes="",
                concepto_despues=obj.concepto or "",
                ip=_get_client_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
            )

            messages.success(request, "Movimiento registrado correctamente.")
            url = reverse("estructura_app:unidad_detalle", args=[unidad.pk])
            return redirect(f"{url}?tab=finanzas")
        else:
            messages.error(request, "Revisa los campos marcados.")
    else:
        form = MovimientoUnidadForm()

    return render(request, "estructura_app/unidad_finanza_form.html", {
        "unidad": unidad,
        "form": form,
        "modo": "crear",
    })


@login_required
@permission_required("estructura_app.change_movimientounidad", raise_exception=True)
def unidad_movimiento_editar(request, pk, mov_id):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)
    mov = get_object_or_404(MovimientoUnidad, pk=mov_id, tenant=tenant, unidad=unidad)

    url_detalle = reverse("estructura_app:unidad_detalle", args=[unidad.pk])
    url_finanzas = f"{url_detalle}?tab=finanzas"

    if mov.anulado:
        messages.warning(request, "Este movimiento está anulado y no se puede editar.")
        return redirect(url_finanzas)

    if request.method == "POST":
        old_fecha = mov.fecha
        old_concepto = mov.concepto

        form = MovimientoUnidadEditarForm(request.POST, instance=mov)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.actualizado_por = request.user
            obj.save(update_fields=["fecha", "concepto", "actualizado_por", "actualizado_en"])

            if old_fecha != obj.fecha or (old_concepto or "") != (obj.concepto or ""):
                MovimientoUnidadLog.objects.create(
                    tenant=tenant,
                    movimiento=obj,
                    accion=MovimientoUnidadLog.ACCION_EDITAR,
                    usuario=request.user,
                    fecha_antes=old_fecha,
                    fecha_despues=obj.fecha,
                    concepto_antes=old_concepto or "",
                    concepto_despues=obj.concepto or "",
                    ip=_get_client_ip(request),
                    user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
                )

            messages.success(request, "Movimiento actualizado correctamente.")
            return redirect(url_finanzas)
        else:
            messages.error(request, "Revisa los campos marcados.")
    else:
        form = MovimientoUnidadEditarForm(instance=mov)

    return render(request, "estructura_app/unidad_finanza_form.html", {
        "unidad": unidad,
        "form": form,
        "modo": "editar",
        "mov": mov,
    })


@login_required
@require_POST
@permission_required("estructura_app.change_movimientounidad", raise_exception=True)
def unidad_movimiento_anular(request, pk, mov_id):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)
    mov = get_object_or_404(MovimientoUnidad, pk=mov_id, tenant=tenant, unidad=unidad)

    motivo = (request.POST.get("motivo") or "").strip()

    old_fecha = mov.fecha
    old_concepto = mov.concepto

    mov.anulado = True
    mov.motivo_anulacion = motivo
    mov.actualizado_por = request.user
    mov.save(update_fields=["anulado", "motivo_anulacion", "actualizado_por", "actualizado_en"])

    MovimientoUnidadLog.objects.create(
        tenant=tenant,
        movimiento=mov,
        accion=MovimientoUnidadLog.ACCION_ANULAR,
        usuario=request.user,
        fecha_antes=old_fecha,
        fecha_despues=mov.fecha,
        concepto_antes=old_concepto or "",
        concepto_despues=mov.concepto or "",
        ip=_get_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
    )

    messages.success(request, "Movimiento anulado correctamente.")

    url_detalle = reverse("estructura_app:unidad_detalle", args=[unidad.pk])
    return redirect(f"{url_detalle}?tab=finanzas")