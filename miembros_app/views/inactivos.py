# -*- coding: utf-8 -*-
"""
miembros_app/views/inactivos.py
Vistas de miembros inactivos, salidas, reingresos y cartas.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET, require_http_methods
from django.utils import timezone
from django.conf import settings

from miembros_app.models import Miembro
from miembros_app.forms import MiembroSalidaForm, MiembroReingresoForm
from nuevo_creyente_app.models import NuevoCreyenteExpediente


# ═══════════════════════════════════════════════════════════════════════════════
# DETALLE MIEMBRO INACTIVO
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def miembro_inactivo_detalle(request, pk):
    """Pantalla para ver el resumen de salida de un registro inactivo."""
    miembro = get_object_or_404(Miembro, pk=pk)

    # Si está activo, redirigir a su detalle
    if miembro.activo:
        if getattr(miembro, "nuevo_creyente", False):
            return redirect("miembros_app:nuevo_creyente_detalle", pk=miembro.pk)
        return redirect("miembros_app:detalle", pk=miembro.pk)

    hoy = timezone.localdate()

    dias_desde_salida = None
    if miembro.fecha_salida:
        try:
            dias_desde_salida = (hoy - miembro.fecha_salida).days
        except Exception:
            pass

    context = {
        "miembro": miembro,
        "hoy": hoy,
        "dias_desde_salida": dias_desde_salida,
        "es_nuevo_creyente": bool(getattr(miembro, "nuevo_creyente", False)),
    }
    
    return render(request, "miembros_app/inactivo_detalle.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# DAR SALIDA
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
@require_http_methods(["GET", "POST"])
def salida_form(request, pk):
    """Formulario para dar salida a un miembro o nuevo creyente."""
    miembro = get_object_or_404(Miembro, pk=pk)

    # Bloqueo: no permitir salida si tiene expediente abierto
    tiene_expediente_abierto = NuevoCreyenteExpediente.objects.filter(
        miembro=miembro,
        estado__iexact="abierto"
    ).exists()

    if tiene_expediente_abierto:
        messages.error(
            request,
            "No se puede dar salida a este nuevo creyente porque "
            "tiene un expediente de seguimiento ABIERTO. "
            "Cierra primero el expediente."
        )
        return redirect("miembros_app:nuevo_creyente_detalle", pk=miembro.pk)

    estado_antes = getattr(miembro, "estado_miembro", "") or ""
    etapa_antes = getattr(miembro, "etapa_actual", "") or ""

    # Permisos
    if not (request.user.is_superuser or request.user.has_perm("miembros_app.change_miembro")):
        return HttpResponseForbidden("No tienes permisos para dar salida a miembros.")

    # Si ya está inactivo, no repetir
    if not miembro.activo:
        messages.info(request, "Este registro ya está inactivo. No se puede registrar una salida de nuevo.")
        return redirect("miembros_app:detalle", pk=miembro.pk)

    es_nuevo_creyente = bool(getattr(miembro, "nuevo_creyente", False))
    
    # Validación adicional para nuevos creyentes
    if es_nuevo_creyente:
        expediente_abierto = NuevoCreyenteExpediente.objects.filter(
            miembro=miembro
        ).exclude(estado="cerrado").first()
        
        if expediente_abierto:
            messages.error(
                request,
                "Este nuevo creyente está en seguimiento. Primero debes cerrar el expediente desde el módulo Nuevo Creyente."
            )
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            return redirect("miembros_app:nuevo_creyente_detalle", pk=miembro.pk)

    if request.method == "POST":
        form = MiembroSalidaForm(request.POST, instance=miembro)
        if form.is_valid():
            miembro_editado = form.save(commit=False)

            # Marcar inactivo
            miembro_editado.activo = False

            # Fecha por defecto
            if not miembro_editado.fecha_salida:
                miembro_editado.fecha_salida = timezone.localdate()

            # Estado según razón configurada
            if miembro_editado.razon_salida and miembro_editado.razon_salida.estado_resultante:
                miembro_editado.estado_miembro = miembro_editado.razon_salida.estado_resultante

            miembro_editado.save()

            # Bitácora
            miembro.log_event(
                tipo="salida",
                titulo="Salida registrada",
                detalle=f"Razón: {miembro_editado.razon_salida or '—'}",
                user=request.user,
                estado_from=estado_antes,
                estado_to=getattr(miembro_editado, "estado_miembro", "") or "",
                etapa_from=etapa_antes,
                etapa_to=getattr(miembro_editado, "etapa_actual", "") or "",
            )

            messages.success(request, "Salida registrada correctamente. El registro ha quedado inactivo.")
            return redirect("miembros_app:inactivo_detalle", pk=miembro_editado.pk)

        messages.error(request, "Hay errores en el formulario. Revisa los campos marcados.")
    else:
        form = MiembroSalidaForm(instance=miembro)

    return render(
        request,
        "miembros_app/salida_form.html",
        {
            "miembro": miembro,
            "form": form,
            "es_nuevo_creyente": es_nuevo_creyente,
        },
    )


@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
def miembro_dar_salida(request, pk):
    """Alias para dar salida a un miembro."""
    return salida_form(request, pk)


@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
def nuevo_creyente_dar_salida(request, pk):
    """Alias para dar salida a un nuevo creyente."""
    return salida_form(request, pk)


# ═══════════════════════════════════════════════════════════════════════════════
# REINCORPORAR MIEMBRO
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
@require_http_methods(["GET", "POST"])
def reincorporar_miembro(request, pk):
    """Reincorpora un miembro inactivo."""
    miembro = get_object_or_404(Miembro, pk=pk)

    # Solo aplica para inactivos
    if miembro.activo:
        messages.info(request, "Este registro ya está activo.")
        if getattr(miembro, "nuevo_creyente", False):
            return redirect("miembros_app:nuevo_creyente_detalle", pk=miembro.pk)
        return redirect("miembros_app:detalle", pk=miembro.pk)

    # Snapshot antes de modificar
    estado_antes = getattr(miembro, "estado_miembro", "") or ""
    etapa_antes = getattr(miembro, "etapa_actual", "") or ""
    razon_txt = "—"
    if getattr(miembro, "razon_salida", None):
        razon_txt = getattr(miembro.razon_salida, "nombre", None) or str(miembro.razon_salida)

    es_nuevo_creyente = bool(getattr(miembro, "nuevo_creyente", False))

    # Para UI: si la razón permite carta
    requiere_carta = bool(
        miembro.razon_salida and getattr(miembro.razon_salida, "permite_carta", False)
    )

    if request.method == "POST":
        form = MiembroReingresoForm(request.POST)

        if form.is_valid():
            # Reactivar
            miembro.activo = True
            miembro.fecha_reingreso = timezone.localdate()

            # Limpiar salida
            miembro.razon_salida = None
            miembro.fecha_salida = None
            miembro.comentario_salida = ""

            # Lógica automática según tipo
            if es_nuevo_creyente:
                miembro.nuevo_creyente = True
                miembro.estado_miembro = "observacion"
                miembro.origen_reingreso = "descarriado"
                miembro.estado_pastoral_reingreso = "reconciliado"
            else:
                miembro.nuevo_creyente = False
                miembro.estado_miembro = "observacion"

                if estado_antes == "descarriado":
                    miembro.origen_reingreso = "descarriado"
                    miembro.estado_pastoral_reingreso = "reconciliado"
                elif estado_antes == "trasladado":
                    miembro.origen_reingreso = "traslado"
                    miembro.estado_pastoral_reingreso = "integrado"
                else:
                    miembro.estado_pastoral_reingreso = (
                        miembro.estado_pastoral_reingreso or "observacion"
                    )

            miembro.save()

            # Bitácora
            miembro.log_event(
                tipo="reingreso",
                titulo="Reincorporación registrada",
                detalle=f"Razón de salida anterior: {razon_txt}",
                user=request.user,
                estado_from=estado_antes,
                estado_to=getattr(miembro, "estado_miembro", "") or "",
                etapa_from=etapa_antes,
                etapa_to=getattr(miembro, "etapa_actual", "") or "",
            )

            if miembro.nuevo_creyente:
                messages.success(request, "Reingreso registrado: Nuevo Creyente (seguimiento).")
                return redirect("miembros_app:nuevo_creyente_detalle", pk=miembro.pk)

            messages.success(request, "Reincorporación registrada: Miembro en observación.")
            return redirect("miembros_app:detalle", pk=miembro.pk)

        messages.error(request, "Hay errores en el formulario.")
    else:
        form = MiembroReingresoForm()

    return render(
        request,
        "miembros_app/reincorporacion_form.html",
        {
            "miembro": miembro,
            "form": form,
            "requiere_carta": requiere_carta,
            "es_nuevo_creyente": es_nuevo_creyente,
            "estado_anterior": estado_antes,
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CARTA DE SALIDA
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def carta_salida_miembro(request, pk):
    """Genera una carta de salida/traslado para un miembro."""
    try:
        miembro = get_object_or_404(Miembro, pk=pk)

        if not miembro.razon_salida or not getattr(miembro.razon_salida, "permite_carta", False):
            messages.error(request, "No aplica carta para este Miembro.")
            return redirect("miembros_app:inactivo_detalle", pk=miembro.pk)

        context = {
            "miembro": miembro,
            "hoy": timezone.localdate(),
            "iglesia_nombre": getattr(settings, "NOMBRE_IGLESIA", "Iglesia Torre Fuerte"),
            "iglesia_ciudad": getattr(settings, "CIUDAD_IGLESIA", "Higüey, República Dominicana"),
            "pastor_principal": getattr(settings, "PASTOR_PRINCIPAL", "Pastor de la iglesia"),
        }

        return render(request, "miembros_app/cartas/carta_salida.html", context)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f"<h2>Error en carta_salida_miembro</h2><pre>{e}</pre>", status=500)