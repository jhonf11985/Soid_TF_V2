# finanzas_app/views/movimientos.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db.models import Sum, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
import json

from miembros_app.models import Miembro
from core.utils_config import get_config

from ..models import (
    MovimientoFinanciero,
    CuentaFinanciera,
    CategoriaMovimiento,
)
from ..forms import (
    MovimientoFinancieroForm,
    MovimientoIngresoForm,
    MovimientoEgresoForm,
)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def movimientos_listado(request):
    """
    Listado de movimientos financieros con filtros, totales y paginación.
    """
    tenant = request.tenant
    
    movimientos = MovimientoFinanciero.objects.filter(
        tenant=tenant
    ).select_related(
        "cuenta", "categoria", "creado_por", "persona_asociada", "unidad"
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
    total_registros = movimientos.count()

    # --------- PAGINACIÓN ----------
    paginator = Paginator(movimientos, 25)
    page = request.GET.get("page", 1)

    try:
        movimientos_page = paginator.page(page)
    except PageNotAnInteger:
        movimientos_page = paginator.page(1)
    except EmptyPage:
        movimientos_page = paginator.page(paginator.num_pages)

    cuentas = CuentaFinanciera.objects.filter(tenant=tenant, esta_activa=True).order_by("nombre")
    categorias = CategoriaMovimiento.objects.filter(tenant=tenant, activo=True).order_by("tipo", "nombre")

    context = {
        "movimientos": movimientos_page,
        "page_obj": movimientos_page,
        "paginator": paginator,
        "total_registros": total_registros,
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
    tenant = request.tenant
    
    if request.method == "POST":
        form = MovimientoFinancieroForm(request.POST, tenant=tenant)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.tenant = tenant
            mov.creado_por = request.user
            mov.save()
            messages.success(request, "Movimiento registrado correctamente.")
            return redirect("finanzas_app:movimientos_listado")
    else:
        form = MovimientoFinancieroForm(tenant=tenant)

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
    Soporta múltiples personas: divide el monto en partes iguales.
    """
    tenant = request.tenant
    
    if request.method == "POST":
        form = MovimientoIngresoForm(request.POST, tenant=tenant)
        
        if form.is_valid():
            # =============================================
            # LÓGICA DE MÚLTIPLES PERSONAS
            # =============================================
            personas_ids_str = request.POST.get("personas_asociadas", "").strip()
            persona_ids = []
            
            if personas_ids_str:
                # Parsear IDs separados por coma
                for pid in personas_ids_str.split(","):
                    pid = pid.strip()
                    if pid.isdigit():
                        persona_ids.append(int(pid))
            
            # Obtener datos base del formulario
            monto_total = form.cleaned_data.get("monto", Decimal("0"))
            fecha = form.cleaned_data.get("fecha")
            cuenta = form.cleaned_data.get("cuenta")
            categoria = form.cleaned_data.get("categoria")
            forma_pago = form.cleaned_data.get("forma_pago")
            referencia = form.cleaned_data.get("referencia", "")
            descripcion = form.cleaned_data.get("descripcion", "")
            unidad = form.cleaned_data.get("unidad")
            
            movimientos_creados = []
            
            if len(persona_ids) > 1:
                # =============================================
                # CASO: MÚLTIPLES PERSONAS - DIVIDIR MONTO
                # =============================================
                cantidad_personas = len(persona_ids)
                
                # Dividir monto en partes iguales (redondeo a 2 decimales)
                monto_por_persona = (monto_total / cantidad_personas).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                
                # Calcular diferencia por redondeo para el último
                monto_acumulado = monto_por_persona * (cantidad_personas - 1)
                monto_ultimo = monto_total - monto_acumulado
                
                # Obtener miembros
                miembros = Miembro.objects.filter(
                    tenant=tenant, 
                    id__in=persona_ids,
                    activo=True
                )
                miembros_dict = {m.id: m for m in miembros}
                
                for idx, pid in enumerate(persona_ids):
                    miembro = miembros_dict.get(pid)
                    if not miembro:
                        continue
                    
                    # El último recibe el monto ajustado por redondeo
                    monto_asignado = monto_ultimo if idx == len(persona_ids) - 1 else monto_por_persona
                    
                    # Crear descripción indicando división
                    desc_dividida = descripcion
                    if descripcion:
                        desc_dividida = f"{descripcion} (Parte {idx + 1}/{cantidad_personas})"
                    else:
                        desc_dividida = f"Ingreso dividido - Parte {idx + 1}/{cantidad_personas}"
                    
                    mov = MovimientoFinanciero(
                        tenant=tenant,
                        tipo="ingreso",
                        estado="confirmado",
                        fecha=fecha,
                        monto=monto_asignado,
                        cuenta=cuenta,
                        categoria=categoria,
                        forma_pago=forma_pago,
                        referencia=referencia,
                        descripcion=desc_dividida,
                        unidad=unidad,
                        persona_asociada=miembro,
                        creado_por=request.user,
                    )
                    mov.save()
                    movimientos_creados.append(mov)
                
                messages.success(
                    request,
                    f"Se crearon {len(movimientos_creados)} ingresos de RD$ {monto_por_persona:,.2f} cada uno "
                    f"(total: RD$ {monto_total:,.2f})."
                )
            
            elif len(persona_ids) == 1:
                # =============================================
                # CASO: UNA SOLA PERSONA
                # =============================================
                miembro = Miembro.objects.filter(
                    tenant=tenant, 
                    id=persona_ids[0],
                    activo=True
                ).first()
                
                mov = form.save(commit=False)
                mov.tenant = tenant
                mov.tipo = "ingreso"
                mov.estado = "confirmado"
                mov.creado_por = request.user
                mov.persona_asociada = miembro
                mov.save()
                movimientos_creados.append(mov)
                
                messages.success(request, "Ingreso registrado y confirmado correctamente.")
            
            else:
                # =============================================
                # CASO: SIN PERSONA (solo unidad o sin origen)
                # =============================================
                mov = form.save(commit=False)
                mov.tenant = tenant
                mov.tipo = "ingreso"
                mov.estado = "confirmado"
                mov.creado_por = request.user
                mov.persona_asociada = None
                mov.save()
                movimientos_creados.append(mov)
                
                messages.success(request, "Ingreso registrado y confirmado correctamente.")

            # Redirección según acción
            accion = request.POST.get("accion")
            if accion == "guardar_nuevo":
                return redirect("finanzas_app:ingreso_crear")
            
            # Si se creó un solo movimiento, ir al detalle
            if len(movimientos_creados) == 1:
                return redirect("finanzas_app:ingreso_detalle", pk=movimientos_creados[0].pk)
            
            # Si se crearon múltiples, ir al listado filtrado por ingresos
            return redirect("/finanzas/movimientos/?tipo=ingreso")
    else:
        form = MovimientoIngresoForm(
            initial={"fecha": timezone.localdate()},
            tenant=tenant
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
    Incluye validación de fondos suficientes y muestra saldo por cuenta.
    """
    tenant = request.tenant
    
    # CALCULAR SALDOS DE TODAS LAS CUENTAS ACTIVAS
    cuentas_con_saldo = {}
    umbral_saldo_bajo = Decimal("5000")

    for cuenta in CuentaFinanciera.objects.filter(tenant=tenant, esta_activa=True):
        movs = MovimientoFinanciero.objects.filter(
            tenant=tenant,
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
        form = MovimientoEgresoForm(request.POST, tenant=tenant)

        if form.is_valid():
            cuenta = form.cleaned_data.get("cuenta")
            monto = form.cleaned_data.get("monto")

            if cuenta and monto:
                saldo_actual = Decimal(str(cuentas_con_saldo.get(cuenta.id, {}).get("saldo", 0)))
                
                if monto > saldo_actual:
                    form.add_error(
                        "monto",
                        f"Fondos insuficientes. Saldo disponible: RD$ {saldo_actual:,.2f}"
                    )
                else:
                    mov = form.save(commit=False)
                    mov.tenant = tenant
                    mov.tipo = "egreso"
                    mov.estado = "confirmado"
                    mov.creado_por = request.user
                    mov.save()

                    messages.success(request, "Egreso registrado y confirmado correctamente.")

                    accion = request.POST.get("accion")
                    if accion == "guardar_nuevo":
                        return redirect("finanzas_app:egreso_crear")

                    return redirect("finanzas_app:egreso_detalle", pk=mov.pk)
    else:
        form = MovimientoEgresoForm(
            initial={"fecha": timezone.localdate()},
            tenant=tenant
        )

    context = {
        "form": form,
        "modo": "crear",
        "cuentas_con_saldo_json": json.dumps(cuentas_con_saldo),
        "umbral_saldo_bajo": float(umbral_saldo_bajo),
    }
    return render(request, "finanzas_app/egreso_form.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.change_movimientofinanciero", raise_exception=True)
def movimiento_editar(request, pk):
    """
    Editar un movimiento existente.
    """
    tenant = request.tenant
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk, tenant=tenant)

    if movimiento.estado == "anulado":
        messages.warning(request, "No se puede editar un movimiento anulado.")
        return redirect("finanzas_app:movimientos_listado")

    # Determinar el form según tipo
    if movimiento.tipo == "ingreso":
        FormClass = MovimientoIngresoForm
        template = "finanzas_app/ingreso_form.html"
    else:
        FormClass = MovimientoEgresoForm
        template = "finanzas_app/egreso_form.html"

    if request.method == "POST":
        form = FormClass(request.POST, instance=movimiento, tenant=tenant)
        
        if form.is_valid():
            # Para edición, usar persona_asociada simple (no múltiple)
            mov = form.save(commit=False)
            
            # Manejar persona_asociada desde el campo múltiple
            personas_ids_str = request.POST.get("personas_asociadas", "").strip()
            if personas_ids_str:
                primer_id = personas_ids_str.split(",")[0].strip()
                if primer_id.isdigit():
                    miembro = Miembro.objects.filter(
                        tenant=tenant, 
                        id=int(primer_id),
                        activo=True
                    ).first()
                    mov.persona_asociada = miembro
                else:
                    mov.persona_asociada = None
            else:
                mov.persona_asociada = None
            
            mov.save()
            messages.success(request, "Movimiento actualizado correctamente.")
            
            if movimiento.tipo == "ingreso":
                return redirect("finanzas_app:ingreso_detalle", pk=mov.pk)
            else:
                return redirect("finanzas_app:egreso_detalle", pk=mov.pk)
    else:
        form = FormClass(instance=movimiento, tenant=tenant)

    # Preparar datos iniciales para el autocomplete multi
    personas_initial = []
    if movimiento.persona_asociada:
        m = movimiento.persona_asociada
        personas_initial.append({
            "id": m.id,
            "nombre": f"{m.nombres} {m.apellidos}".strip(),
            "codigo": getattr(m, "codigo_miembro", "") or "",
        })

    context = {
        "form": form,
        "movimiento": movimiento,
        "modo": "editar",
        "personas_initial_json": json.dumps(personas_initial),
    }
    return render(request, template, context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.delete_movimientofinanciero", raise_exception=True)
def movimiento_anular(request, pk):
    """
    Anular un movimiento (no lo elimina, cambia el estado).
    Si es un egreso vinculado a una CxP, revierte el pago automáticamente.
    """
    tenant = request.tenant
    movimiento = get_object_or_404(MovimientoFinanciero, pk=pk, tenant=tenant)

    if movimiento.estado == "anulado":
        messages.warning(request, "Este movimiento ya está anulado.")
        return redirect("finanzas_app:movimientos_listado")

    if request.method == "POST":
        motivo = (request.POST.get("motivo") or "").strip()
        if not motivo:
            messages.error(request, "Debes indicar el motivo de la anulación.")
            return redirect("finanzas_app:movimiento_anular", pk=movimiento.pk)

        # Revertir pago si está vinculado a una CxP
        cxp = getattr(movimiento, 'cuenta_por_pagar', None)

        if cxp and movimiento.tipo == "egreso":
            monto_a_revertir = movimiento.monto
            cxp.monto_pagado = max(
                Decimal("0"),
                (cxp.monto_pagado or Decimal("0")) - monto_a_revertir
            )

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

        movimiento.estado = "anulado"
        movimiento.motivo_anulacion = motivo
        movimiento.anulado_por = request.user
        movimiento.anulado_en = timezone.now()
        movimiento.save()

        messages.warning(request, f"Movimiento #{movimiento.pk} anulado correctamente.")
        return redirect("finanzas_app:movimientos_listado")

    context = {
        "modo": "movimiento",
        "movimiento": movimiento,
        "back_url": request.META.get("HTTP_REFERER") or reverse("finanzas_app:movimientos_listado"),
        "tiene_cxp": bool(getattr(movimiento, 'cuenta_por_pagar', None)),
    }

    return render(request, "finanzas_app/anulacion_confirmar.html", context)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def ingreso_detalle(request, pk):
    """
    Vista de detalle para un INGRESO.
    """
    tenant = request.tenant
    ingreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="ingreso", tenant=tenant)

    context = {
        "ingreso": ingreso,
    }
    return render(request, "finanzas_app/ingreso_detalle.html", context)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def egreso_detalle(request, pk):
    """
    Vista de detalle para un EGRESO.
    """
    tenant = request.tenant
    egreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="egreso", tenant=tenant)

    context = {
        "egreso": egreso,
    }
    return render(request, "finanzas_app/egreso_detalle.html", context)


@login_required
@require_GET
@permission_required("finanzas_app.add_movimientofinanciero", raise_exception=True)
def buscar_miembros_finanzas(request):
    """
    Devuelve un JSON con miembros activos para el modal de búsqueda.
    """
    tenant = request.tenant
    q = request.GET.get("q", "").strip()

    miembros = Miembro.objects.filter(tenant=tenant, activo=True)

    if q:
        miembros = miembros.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(codigo_miembro__icontains=q)
        )

    miembros = miembros.order_by("nombres", "apellidos")[:50]

    data = []
    for m in miembros:
        data.append({
            "id": m.id,
            "nombre": f"{m.nombres} {m.apellidos}".strip(),
            "codigo": getattr(m, "codigo_miembro", "") or "",
        })

    return JsonResponse({"success": True, "resultados": data})


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def movimientos_listado_print(request):
    """
    Vista para imprimir listado de movimientos.
    """
    tenant = request.tenant
    
    # Reutilizar la lógica de filtros
    movimientos = MovimientoFinanciero.objects.filter(
        tenant=tenant
    ).select_related(
        "cuenta", "categoria", "creado_por", "persona_asociada"
    ).exclude(estado="anulado").order_by("-fecha", "-creado_en")

    # Aplicar filtros
    tipo = request.GET.get("tipo")
    cuenta_id = request.GET.get("cuenta")
    categoria_id = request.GET.get("categoria")
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    if tipo == "transferencia":
        movimientos = movimientos.filter(es_transferencia=True)
    elif tipo in ["ingreso", "egreso"]:
        movimientos = movimientos.filter(tipo=tipo).exclude(es_transferencia=True)

    if cuenta_id:
        movimientos = movimientos.filter(cuenta_id=cuenta_id)
        cuenta_obj = CuentaFinanciera.objects.filter(pk=cuenta_id, tenant=tenant).first()
    else:
        cuenta_obj = None

    if categoria_id:
        movimientos = movimientos.filter(categoria_id=categoria_id)
        categoria_obj = CategoriaMovimiento.objects.filter(pk=categoria_id, tenant=tenant).first()
    else:
        categoria_obj = None

    if fecha_desde:
        movimientos = movimientos.filter(fecha__gte=fecha_desde)

    if fecha_hasta:
        movimientos = movimientos.filter(fecha__lte=fecha_hasta)

    # Totales
    totales = movimientos.aggregate(
        total_ingresos=Sum("monto", filter=Q(tipo="ingreso")),
        total_egresos=Sum("monto", filter=Q(tipo="egreso")),
    )

    CFG = get_config()

    context = {
        "CFG": CFG,
        "movimientos": movimientos[:500],
        "total_ingresos": totales.get("total_ingresos") or 0,
        "total_egresos": totales.get("total_egresos") or 0,
        "balance": (totales.get("total_ingresos") or 0) - (totales.get("total_egresos") or 0),
        "f_tipo": tipo or "",
        "f_cuenta": cuenta_obj,
        "f_categoria": categoria_obj,
        "f_fecha_desde": fecha_desde or "",
        "f_fecha_hasta": fecha_hasta or "",
        "auto_print": True,
    }
    return render(request, "finanzas_app/movimientos_listado_print.html", context)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def ingreso_recibo(request, pk):
    """
    Vista para imprimir recibo de ingreso.
    """
    tenant = request.tenant
    ingreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="ingreso", tenant=tenant)
    CFG = get_config()

    context = {
        "CFG": CFG,
        "ingreso": ingreso,
        "auto_print": True,
    }
    return render(request, "finanzas_app/recibos/ingreso_recibo.html", context)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def ingreso_general_pdf(request, pk):
    """
    Vista para generar PDF de ingreso.
    """
    tenant = request.tenant
    ingreso = get_object_or_404(MovimientoFinanciero, pk=pk, tipo="ingreso", tenant=tenant)
    CFG = get_config()

    context = {
        "CFG": CFG,
        "ingreso": ingreso,
        "auto_print": False,
    }
    return render(request, "finanzas_app/recibos/ingreso_general.html", context)