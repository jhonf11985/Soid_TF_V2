from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.db.models import Q
import re

from miembros_app.models import Miembro, ESTADO_MIEMBRO_CHOICES
from .models import (
    AccesoActualizacionDatos,
    SolicitudActualizacionMiembro,
    SolicitudAltaMiembro,
    AltaMasivaConfig,
    ActualizacionDatosConfig,
    AccesoAltaFamilia,
    AltaFamiliaLog,
)
from .forms import SolicitudActualizacionForm, SolicitudAltaPublicaForm, ActualizacionDatosConfigForm
from .services import aplicar_solicitud_a_miembro, crear_miembro_desde_solicitud_alta, aplicar_alta_familia
from .services import _normalizar_cedula_rd
from .utils import traducir_user_agent


# ==========================================================
# HELPERS
# ==========================================================
def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_tenant(request):
    """Obtiene el tenant del request (asignado por middleware)."""
    return getattr(request, 'tenant', None)


def _require_tenant(request):
    """Retorna tenant o lanza 404 si no existe."""
    tenant = _get_tenant(request)
    if not tenant:
        from django.http import Http404
        raise Http404("Tenant no configurado")
    return tenant


# ==========================================================
# FAMILIA - ADMIN
# ==========================================================
@login_required
def familia_links_lista(request):
    """Admin: lista links existentes."""
    tenant = _require_tenant(request)
    q = (request.GET.get("q") or "").strip()

    items = AccesoAltaFamilia.objects.filter(tenant=tenant).order_by("-creado_en")
    if q:
        items = items.filter(token__icontains=q)

    return render(request, "actualizacion_datos_miembros/link_familias_lista.html", {
        "items": items,
        "q": q,
    })


@login_required
def familia_generar_link(request):
    """Admin: crea un link neutral."""
    tenant = _require_tenant(request)
    link = None

    if request.method == "POST":
        acceso = AccesoAltaFamilia.objects.create(tenant=tenant, activo=True)
        link = request.build_absolute_uri(
            reverse("actualizacion_datos_miembros:familia_formulario_publico", kwargs={"token": acceso.token})
        )
        messages.success(request, "Link creado correctamente.")

    return render(request, "actualizacion_datos_miembros/link_familias.html", {"link": link})


@login_required
def familia_alertas(request):
    """Admin: muestra alertas/conflictos detectados."""
    tenant = _require_tenant(request)
    tipo_filtro = (request.GET.get("tipo") or "").strip().lower()

    logs_con_alertas = AltaFamiliaLog.objects.filter(
        tenant=tenant,
        alertas__isnull=False
    ).exclude(alertas=[]).select_related("principal").order_by("-creado_en")

    alertas = []
    for log in logs_con_alertas:
        for alerta_data in log.alertas:
            if isinstance(alerta_data, str):
                alerta = {"mensaje": alerta_data, "tipo": "conflicto", "nivel": "warning"}
            else:
                alerta = {
                    "mensaje": alerta_data.get("motivo") or alerta_data.get("mensaje") or str(alerta_data),
                    "tipo": alerta_data.get("tipo", "conflicto"),
                    "nivel": alerta_data.get("nivel", "warning"),
                }
            alerta["principal"] = log.principal
            alerta["solicitud_id"] = log.pk
            alerta["fecha"] = log.creado_en

            if tipo_filtro and alerta["tipo"].lower() != tipo_filtro:
                continue
            alertas.append(alerta)

    total_alertas = len(alertas)
    alertas_conflicto = sum(1 for a in alertas if a.get("nivel") == "error")
    alertas_info = total_alertas - alertas_conflicto

    return render(request, "actualizacion_datos_miembros/alta_familias_alerta.html", {
        "alertas": alertas,
        "total_alertas": total_alertas,
        "alertas_conflicto": alertas_conflicto,
        "alertas_info": alertas_info,
        "tipo_filtro": tipo_filtro,
    })


def api_buscar_miembros(request):
    """API pública para buscar miembros (autocomplete)."""
    tenant = _get_tenant(request)
    q = (request.GET.get("q") or "").strip()
    
    if len(q) < 2:
        return JsonResponse({"success": True, "resultados": []})

    token = (request.GET.get("token") or "").strip()
    if token:
        if not AccesoAltaFamilia.objects.filter(token=token, activo=True).exists():
            return JsonResponse({"success": True, "resultados": []})

    filtro = (request.GET.get("filtro") or "").strip().lower()
    try:
        limit = int(request.GET.get("limit") or 15)
    except ValueError:
        limit = 15
    limit = max(1, min(limit, 25))

    qs = Miembro.objects.filter(
        Q(nombres__icontains=q) |
        Q(apellidos__icontains=q) |
        Q(cedula__icontains=q)
    )
    
    # Filtrar por tenant si existe
    if tenant:
        qs = qs.filter(tenant=tenant)

    if filtro in ("activo", "activos"):
        if hasattr(Miembro, "activo"):
            qs = qs.filter(activo=True)
        elif hasattr(Miembro, "estado"):
            qs = qs.filter(estado__iexact="ACTIVO")

    qs = qs.order_by("nombres", "apellidos")[:limit]

    resultados = []
    for m in qs:
        nombre = f"{m.nombres} {m.apellidos}".strip()
        resultados.append({
            "id": m.id,
            "nombre": nombre,
            "codigo": getattr(m, "codigo", "") or getattr(m, "numero_miembro", "") or "",
            "telefono": getattr(m, "telefono", "") or "—",
        })

    return JsonResponse({"success": True, "resultados": resultados})


@login_required
def generar_link_familia(request, miembro_id):
    tenant = _require_tenant(request)
    jefe = get_object_or_404(Miembro, pk=miembro_id, tenant=tenant)

    acceso, created = AccesoAltaFamilia.objects.get_or_create(
        tenant=tenant,
        defaults={"activo": True}
    )
    if not acceso.activo:
        acceso.activo = True
        acceso.save(update_fields=["activo", "actualizado_en"])

    link = request.build_absolute_uri(
        reverse("actualizacion_datos_miembros:familia_formulario_publico", kwargs={"token": acceso.token})
    )

    return render(request, "actualizacion_datos_miembros/link_familia.html", {
        "jefe": jefe,
        "acceso": acceso,
        "link": link,
        "created": created,
    })


def familia_formulario_publico(request, token):
    """Público: formulario de alta de familia."""
    acceso = get_object_or_404(AccesoAltaFamilia, token=token, activo=True)
    tenant = acceso.tenant
    CFG = None

    if request.method == "POST":
        principal_id = (request.POST.get("principal_id") or "").strip()
        conyuge_id = (request.POST.get("conyuge_id") or "").strip()
        padre_id = (request.POST.get("padre_id") or "").strip()
        madre_id = (request.POST.get("madre_id") or "").strip()
        hijos_ids = request.POST.getlist("hijos_ids")

        if not principal_id:
            messages.error(request, "Debes seleccionar un miembro principal antes de enviar.")
            return render(request, "actualizacion_datos_miembros/familia_publico.html", {"CFG": CFG, "acceso": acceso})

        try:
            principal = Miembro.objects.get(id=int(principal_id), tenant=tenant)
        except (Miembro.DoesNotExist, ValueError):
            messages.error(request, "El miembro principal seleccionado no es válido.")
            return render(request, "actualizacion_datos_miembros/familia_publico.html", {"CFG": CFG, "acceso": acceso})

        conyuge_id_int = int(conyuge_id) if conyuge_id else None
        padre_id_int = int(padre_id) if padre_id else None
        madre_id_int = int(madre_id) if madre_id else None
        hijos_ids_int = []
        for x in hijos_ids:
            x = (x or "").strip()
            if x:
                try:
                    hijos_ids_int.append(int(x))
                except ValueError:
                    continue

        ip_origen = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
        if ip_origen and "," in ip_origen:
            ip_origen = ip_origen.split(",")[0].strip()
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]

        AltaFamiliaLog.objects.create(
            tenant=tenant,
            acceso=acceso,
            principal=principal,
            conyuge_id=conyuge_id_int,
            padre_id=padre_id_int,
            madre_id=madre_id_int,
            hijos_ids=hijos_ids_int,
            estado="pendiente",
            ip_origen=ip_origen,
            user_agent=user_agent,
        )

        acceso.ultimo_envio_en = timezone.now()
        acceso.save(update_fields=["ultimo_envio_en", "actualizado_en"])

        return render(request, "actualizacion_datos_miembros/familia_ok.html", {
            "CFG": CFG,
            "principal": principal,
        })

    return render(request, "actualizacion_datos_miembros/familia_publico.html", {"CFG": CFG, "acceso": acceso})


@login_required
def familia_solicitudes_lista(request):
    """Admin: lista de solicitudes de alta de familia."""
    tenant = _require_tenant(request)
    
    qs_all = AltaFamiliaLog.objects.filter(tenant=tenant).select_related("principal", "acceso").order_by("-creado_en")

    total_count = qs_all.count()
    pendientes_count = qs_all.filter(estado="pendiente").count()
    aplicadas_count = qs_all.filter(estado="aplicada").count()
    rechazadas_count = qs_all.filter(estado="rechazada").count()

    qs = qs_all
    estado = (request.GET.get("estado") or "").strip()
    if estado:
        qs = qs.filter(estado=estado)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(principal__nombres__icontains=q) |
            Q(principal__apellidos__icontains=q) |
            Q(principal__codigo__icontains=q)
        )

    return render(request, "actualizacion_datos_miembros/familia_solicitudes_lista.html", {
        "solicitudes": qs[:300],
        "estado": estado,
        "q": q,
        "Estados": AltaFamiliaLog.Estados,
        "total_count": total_count,
        "pendientes_count": pendientes_count,
        "aplicadas_count": aplicadas_count,
        "rechazadas_count": rechazadas_count,
    })


@login_required
def familia_solicitud_detalle(request, pk):
    tenant = _require_tenant(request)
    s = get_object_or_404(AltaFamiliaLog.objects.select_related("principal", "acceso"), pk=pk, tenant=tenant)

    return render(request, "actualizacion_datos_miembros/familia_solicitud_detalle.html", {
        "s": s,
        "Estados": AltaFamiliaLog.Estados,
        "conyuge": s.get_conyuge(),
        "padre": s.get_padre(),
        "madre": s.get_madre(),
        "hijos": s.get_hijos(),
    })


@login_required
def familia_solicitud_aplicar(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    tenant = _require_tenant(request)
    s = get_object_or_404(AltaFamiliaLog, pk=pk, tenant=tenant)

    if s.estado != AltaFamiliaLog.Estados.PENDIENTE:
        messages.info(request, "Esta solicitud ya fue procesada.")
        return redirect("actualizacion_datos_miembros:familia_solicitud_detalle", pk=s.pk)

    try:
        resultado = aplicar_alta_familia(
            jefe_id=s.principal_id,
            conyuge_id=s.conyuge_id,
            padre_id=s.padre_id,
            madre_id=s.madre_id,
            hijos_ids=s.hijos_ids or [],
        )
        s.relaciones_creadas = resultado.get("relaciones_creadas", [])
        s.alertas = resultado.get("alertas", [])
    except Exception as e:
        messages.error(request, f"Error al aplicar relaciones: {e}")
        return redirect("actualizacion_datos_miembros:familia_solicitud_detalle", pk=s.pk)

    s.estado = AltaFamiliaLog.Estados.APLICADA
    s.revisado_en = timezone.now()
    s.revisado_por = request.user
    s.save()

    messages.success(request, "Solicitud aplicada ✅ Las relaciones familiares fueron creadas.")
    return redirect("actualizacion_datos_miembros:familia_solicitud_detalle", pk=s.pk)


@login_required
def familia_solicitud_rechazar(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    tenant = _require_tenant(request)
    s = get_object_or_404(AltaFamiliaLog, pk=pk, tenant=tenant)

    if s.estado != AltaFamiliaLog.Estados.PENDIENTE:
        messages.info(request, "Esta solicitud ya fue procesada.")
        return redirect("actualizacion_datos_miembros:familia_solicitud_detalle", pk=s.pk)

    nota = (request.POST.get("nota_admin") or "").strip()
    s.estado = AltaFamiliaLog.Estados.RECHAZADA
    s.nota_admin = nota
    s.revisado_en = timezone.now()
    s.revisado_por = request.user
    s.save()

    messages.success(request, "Solicitud rechazada.")
    return redirect("actualizacion_datos_miembros:familia_solicitud_detalle", pk=s.pk)


# ==========================================================
# CONFIG - ACTUALIZACIÓN DE DATOS
# ==========================================================
@login_required
def actualizacion_config(request):
    tenant = _require_tenant(request)
    config = ActualizacionDatosConfig.get_solo(tenant)

    if request.method == "POST":
        form = ActualizacionDatosConfigForm(request.POST)
        if form.is_valid():
            config.activo = bool(form.cleaned_data.get("activo"))
            config.campos_permitidos = form.cleaned_data.get("campos_permitidos") or []
            config.actualizado_en = timezone.now()
            config.save(update_fields=["activo", "campos_permitidos", "actualizado_en"])

            messages.success(request, "Configuración guardada correctamente.")
            return redirect("actualizacion_datos_miembros:actualizacion_config")
        else:
            messages.error(request, "Revisa el formulario. Hay errores.")
    else:
        form = ActualizacionDatosConfigForm(initial={
            "activo": config.activo,
            "campos_permitidos": config.campos_permitidos,
        })

    return render(request, "actualizacion_datos_miembros/actualizacion_config.html", {
        "form": form,
        "config": config,
        "Estados": SolicitudActualizacionMiembro.Estados,
        "EstadosAlta": SolicitudAltaMiembro.Estados,
    })


# ==========================================================
# CONFIG - ALTA MASIVA
# ==========================================================
@login_required
def alta_masiva_config(request):
    tenant = _require_tenant(request)
    config = AltaMasivaConfig.get_solo(tenant)

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()

        if accion == "abrir":
            config.activo = True
            config.save(update_fields=["activo", "actualizado_en"])
            messages.success(request, "Alta masiva ACTIVADA.")
        elif accion == "cerrar":
            config.activo = False
            config.save(update_fields=["activo", "actualizado_en"])
            messages.warning(request, "Alta masiva CERRADA.")
        else:
            messages.error(request, "Acción inválida.")

        return redirect("actualizacion_datos_miembros:alta_masiva_config")

    return render(request, "actualizacion_datos_miembros/alta_masiva_config.html", {
        "config": config,
        "Estados": SolicitudActualizacionMiembro.Estados,
        "EstadosAlta": SolicitudAltaMiembro.Estados,
    })


@login_required
def alta_masiva_link(request):
    tenant = _require_tenant(request)
    config = AltaMasivaConfig.get_solo(tenant)

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()

        if accion == "abrir":
            config.activo = True
            config.save(update_fields=["activo", "actualizado_en"])
            messages.success(request, "Alta masiva ACTIVADA.")
            return redirect("actualizacion_datos_miembros:alta_masiva_link")

        elif accion == "cerrar":
            config.activo = False
            config.save(update_fields=["activo", "actualizado_en"])
            messages.success(request, "Alta masiva CERRADA.")
            return redirect("actualizacion_datos_miembros:alta_masiva_link")

        elif accion == "guardar_mensaje":
            mensaje = (request.POST.get("mensaje_compartir") or "").strip()
            if mensaje:
                config.mensaje_compartir = mensaje
                config.save(update_fields=["mensaje_compartir", "actualizado_en"])
                messages.success(request, "Mensaje de WhatsApp guardado.")
            else:
                messages.warning(request, "El mensaje no puede estar vacío.")
            return redirect("actualizacion_datos_miembros:alta_masiva_link")

        else:
            messages.error(request, "Acción inválida.")
            return redirect("actualizacion_datos_miembros:alta_masiva_link")

    link = request.build_absolute_uri(reverse("actualizacion_datos_miembros:alta_publica"))

    return render(request, "actualizacion_datos_miembros/alta_masiva_link.html", {
        "link": link,
        "public_url": link,
        "config": config,
        "Estados": SolicitudActualizacionMiembro.Estados,
        "EstadosAlta": SolicitudAltaMiembro.Estados,
    })


# ==========================================================
# LINKS - ACTUALIZACIÓN DE DATOS
# ==========================================================
@login_required
def links_lista(request):
    tenant = _require_tenant(request)
    q = (request.GET.get("q") or "").strip()

    qs = (
        Miembro.objects
        .filter(tenant=tenant)
        .select_related("acceso_actualizacion_datos")
        .order_by("apellidos", "nombres")
    )

    if q:
        qs = qs.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(codigo__icontains=q) |
            Q(telefono__icontains=q)
        )

    return render(request, "actualizacion_datos_miembros/links_lista.html", {
        "miembros": qs[:300],
        "q": q,
        "Estados": SolicitudActualizacionMiembro.Estados,
        "EstadosAlta": SolicitudAltaMiembro.Estados,
    })


@login_required
def generar_link_miembro(request, miembro_id):
    tenant = _require_tenant(request)
    miembro = get_object_or_404(Miembro, pk=miembro_id, tenant=tenant)

    acceso, created = AccesoActualizacionDatos.objects.get_or_create(
        miembro=miembro,
        defaults={"tenant": tenant}
    )
    if not acceso.activo:
        acceso.activo = True
        acceso.save(update_fields=["activo", "actualizado_en"])

    link = request.build_absolute_uri(
        reverse("actualizacion_datos_miembros:formulario_publico", kwargs={"token": acceso.token})
    )

    return render(request, "actualizacion_datos_miembros/link_miembro.html", {
        "miembro": miembro,
        "acceso": acceso,
        "link": link,
        "public_url": link,
        "created": created,
    })


# ==========================================================
# ADMIN - ALTAS (Registro masivo)
# ==========================================================
@login_required
def altas_lista(request):
    tenant = _require_tenant(request)
    qs = SolicitudAltaMiembro.objects.filter(tenant=tenant)

    estado = (request.GET.get("estado") or "").strip()
    if estado:
        qs = qs.filter(estado=estado)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(telefono__icontains=q)
        )

    return render(request, "actualizacion_datos_miembros/altas_lista.html", {
        "altas": qs[:300],
        "estado": estado,
        "q": q,
        "Estados": SolicitudAltaMiembro.Estados,
        "estado_miembro_choices": ESTADO_MIEMBRO_CHOICES,
    })


@login_required
def alta_detalle(request, pk):
    tenant = _require_tenant(request)
    s = get_object_or_404(SolicitudAltaMiembro, pk=pk, tenant=tenant)
    ua_legible = traducir_user_agent(s.user_agent)

    return render(request, "actualizacion_datos_miembros/alta_detalle.html", {
        "s": s,
        "Estados": SolicitudAltaMiembro.Estados,
        "ua_legible": ua_legible,
    })


@login_required
def alta_aprobar(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    tenant = _require_tenant(request)
    s = get_object_or_404(SolicitudAltaMiembro, pk=pk, tenant=tenant)
    
    if s.estado != SolicitudAltaMiembro.Estados.PENDIENTE:
        messages.info(request, "Esta solicitud ya fue procesada.")
        return redirect("actualizacion_datos_miembros:alta_detalle", pk=s.pk)

    try:
        miembro = crear_miembro_desde_solicitud_alta(s)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect("actualizacion_datos_miembros:alta_detalle", pk=s.pk)

    s.estado = SolicitudAltaMiembro.Estados.APROBADA
    s.revisado_en = timezone.now()
    s.revisado_por = request.user
    s.save(update_fields=["estado", "revisado_en", "revisado_por"])

    messages.success(request, f"Solicitud aprobada ✅ Miembro creado: {miembro.nombres} {miembro.apellidos}")
    return redirect("miembros_app:detalle", pk=miembro.pk)


@login_required
def alta_rechazar(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    tenant = _require_tenant(request)
    s = get_object_or_404(SolicitudAltaMiembro, pk=pk, tenant=tenant)
    
    if s.estado != SolicitudAltaMiembro.Estados.PENDIENTE:
        messages.info(request, "Esta solicitud ya fue procesada.")
        return redirect("actualizacion_datos_miembros:alta_detalle", pk=s.pk)

    nota = (request.POST.get("nota_admin") or "").strip()
    s.estado = SolicitudAltaMiembro.Estados.RECHAZADA
    s.nota_admin = nota
    s.revisado_en = timezone.now()
    s.revisado_por = request.user
    s.save(update_fields=["estado", "nota_admin", "revisado_en", "revisado_por"])

    messages.success(request, "Solicitud rechazada.")
    return redirect("actualizacion_datos_miembros:alta_detalle", pk=s.pk)


@login_required
def altas_aprobar_masivo(request):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    tenant = _require_tenant(request)
    ids_str = request.POST.get("ids", "")
    if not ids_str:
        messages.warning(request, "No se seleccionaron solicitudes.")
        return redirect("actualizacion_datos_miembros:altas_lista")

    ids = [int(i) for i in ids_str.split(",") if i.strip().isdigit()]

    solicitudes = SolicitudAltaMiembro.objects.filter(
        tenant=tenant,
        pk__in=ids,
        estado=SolicitudAltaMiembro.Estados.PENDIENTE
    )

    ok = 0
    fail = 0
    errores = []

    for s in solicitudes:
        try:
            crear_miembro_desde_solicitud_alta(s)
        except ValueError as e:
            fail += 1
            if len(errores) < 5:
                errores.append(f"Solicitud #{s.pk}: {e}")
            continue

        s.estado = SolicitudAltaMiembro.Estados.APROBADA
        s.revisado_en = timezone.now()
        s.revisado_por = request.user
        s.save(update_fields=["estado", "revisado_en", "revisado_por"])
        ok += 1

    if ok:
        messages.success(request, f"{ok} solicitud(es) aprobada(s) y convertida(s) en Miembro ✅")
    if fail:
        messages.warning(request, f"{fail} solicitud(es) no se aprobaron por duplicados/errores.")
        for err in errores:
            messages.error(request, err)
    if not ok and not fail:
        messages.info(request, "No se encontraron solicitudes pendientes para aprobar.")

    return redirect("actualizacion_datos_miembros:altas_lista")


@login_required
def altas_rechazar_masivo(request):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    tenant = _require_tenant(request)
    ids_str = request.POST.get("ids", "")
    if not ids_str:
        messages.warning(request, "No se seleccionaron solicitudes.")
        return redirect("actualizacion_datos_miembros:altas_lista")

    ids = [int(i) for i in ids_str.split(",") if i.strip().isdigit()]
    nota = (request.POST.get("nota_admin") or "").strip()

    solicitudes = SolicitudAltaMiembro.objects.filter(
        tenant=tenant,
        pk__in=ids,
        estado=SolicitudAltaMiembro.Estados.PENDIENTE
    )

    count = 0
    for s in solicitudes:
        s.estado = SolicitudAltaMiembro.Estados.RECHAZADA
        s.nota_admin = nota
        s.revisado_en = timezone.now()
        s.revisado_por = request.user
        s.save(update_fields=["estado", "nota_admin", "revisado_en", "revisado_por"])
        count += 1

    if count:
        messages.success(request, f"{count} solicitud(es) rechazada(s).")
    else:
        messages.info(request, "No se encontraron solicitudes pendientes para rechazar.")

    return redirect("actualizacion_datos_miembros:altas_lista")


@login_required
def alta_cambiar_estado_miembro(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    tenant = _require_tenant(request)
    s = get_object_or_404(SolicitudAltaMiembro, pk=pk, tenant=tenant)

    if s.estado != SolicitudAltaMiembro.Estados.PENDIENTE:
        messages.info(request, "No se puede modificar una solicitud ya procesada.")
        return redirect("actualizacion_datos_miembros:altas_lista")

    nuevo_estado = (request.POST.get("estado_miembro") or "").strip()
    estados_validos = [c[0] for c in ESTADO_MIEMBRO_CHOICES]
    if nuevo_estado not in estados_validos:
        messages.error(request, "Estado de miembro inválido.")
        return redirect("actualizacion_datos_miembros:altas_lista")

    s.estado_miembro = nuevo_estado
    s.save(update_fields=["estado_miembro"])

    messages.success(request, "Estado del miembro actualizado.")
    return redirect("actualizacion_datos_miembros:altas_lista")


# ==========================================================
# PÚBLICO - ALTA MASIVA
# ==========================================================
def alta_publica(request):
    """Formulario público para registro (alta masiva)."""
    tenant = _get_tenant(request)
    if not tenant:
        return render(request, "actualizacion_datos_miembros/alta_cerrada.html", {})
    
    config = AltaMasivaConfig.get_solo(tenant)
    if not config.activo:
        return render(request, "actualizacion_datos_miembros/alta_cerrada.html", {})

    if request.method == "POST":
        form = SolicitudAltaPublicaForm(request.POST, request.FILES)

        if form.is_valid():
            tel = (form.cleaned_data.get("telefono") or "").strip()
            cedula = _normalizar_cedula_rd(form.cleaned_data.get("cedula") or "")

            # Anti-duplicado por teléfono
            if SolicitudAltaMiembro.objects.filter(
                tenant=tenant,
                telefono=tel,
                estado=SolicitudAltaMiembro.Estados.PENDIENTE
            ).exists():
                form.add_error("telefono", "Este teléfono ya tiene una solicitud pendiente.")
                return render(request, "actualizacion_datos_miembros/alta_publico.html", {"form": form})

            digits = re.sub(r"\D+", "", tel)
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]
            tel_norm = digits[:10] if len(digits) >= 10 else ""

            if tel_norm and Miembro.objects.filter(tenant=tenant, telefono_norm=tel_norm).exists():
                form.add_error("telefono", "Este teléfono ya está registrado en el sistema.")
                return render(request, "actualizacion_datos_miembros/alta_publico.html", {"form": form})

            # Anti-duplicado por cédula
            if cedula:
                if SolicitudAltaMiembro.objects.filter(
                    tenant=tenant,
                    cedula=cedula,
                    estado=SolicitudAltaMiembro.Estados.PENDIENTE
                ).exists():
                    form.add_error("cedula", "Esta cédula ya tiene una solicitud pendiente.")
                    return render(request, "actualizacion_datos_miembros/alta_publico.html", {"form": form})

                if Miembro.objects.filter(tenant=tenant, cedula=cedula).exists():
                    form.add_error("cedula", "Esta cédula ya está registrada en el sistema.")
                    return render(request, "actualizacion_datos_miembros/alta_publico.html", {"form": form})

            solicitud = form.save(commit=False)
            solicitud.tenant = tenant
            solicitud.cedula = cedula
            solicitud.telefono = tel
            solicitud.estado = SolicitudAltaMiembro.Estados.PENDIENTE
            solicitud.ip_origen = _get_client_ip(request)
            solicitud.user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:255]
            solicitud.save()

            return redirect("actualizacion_datos_miembros:alta_ok")
        else:
            messages.error(request, "Revisa los campos marcados. Hay errores en el formulario.")
    else:
        form = SolicitudAltaPublicaForm()

    return render(request, "actualizacion_datos_miembros/alta_publico.html", {"form": form})


def alta_ok(request):
    return render(request, "actualizacion_datos_miembros/alta_ok.html")


# ==========================================================
# PÚBLICO - ACTUALIZACIÓN DE DATOS
# ==========================================================
def formulario_actualizacion_publico(request, token):
    acceso = get_object_or_404(AccesoActualizacionDatos, token=token)
    tenant = acceso.tenant

    if not acceso.activo:
        return render(request, "actualizacion_datos_miembros/publico_inactivo.html", {
            "miembro": acceso.miembro,
        })

    miembro = acceso.miembro

    config = ActualizacionDatosConfig.get_solo(tenant)
    if not config.activo:
        return render(request, "actualizacion_datos_miembros/publico_inactivo.html", {
            "miembro": acceso.miembro,
        })

    allowed_fields = config.campos_permitidos or None

    if request.method == "POST":
        form = SolicitudActualizacionForm(request.POST, allowed_fields=allowed_fields)

        if form.is_valid():
            if SolicitudActualizacionMiembro.objects.filter(
                miembro=miembro,
                estado=SolicitudActualizacionMiembro.Estados.PENDIENTE
            ).exists():
                messages.info(request, "Ya tienes una solicitud pendiente. El equipo la revisará pronto.")
                return redirect("actualizacion_datos_miembros:formulario_ok", token=acceso.token)

            solicitud = form.save(commit=False)
            solicitud.tenant = tenant
            solicitud.miembro = miembro
            solicitud.estado = SolicitudActualizacionMiembro.Estados.PENDIENTE
            solicitud.ip_origen = _get_client_ip(request)
            solicitud.user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:255]
            solicitud.save()

            acceso.ultimo_envio_en = timezone.now()
            acceso.activo = False
            acceso.save(update_fields=["ultimo_envio_en", "activo", "actualizado_en"])

            return redirect("actualizacion_datos_miembros:formulario_ok", token=acceso.token)
        else:
            messages.error(request, "Revisa los campos marcados. Hay errores en el formulario.")
    else:
        initial = {
            "telefono": miembro.telefono,
            "whatsapp": miembro.whatsapp,
            "email": miembro.email,
            "direccion": miembro.direccion,
            "sector": miembro.sector,
            "ciudad": miembro.ciudad,
            "provincia": miembro.provincia,
            "codigo_postal": miembro.codigo_postal,
            "empleador": miembro.empleador,
            "puesto": miembro.puesto,
            "telefono_trabajo": miembro.telefono_trabajo,
            "direccion_trabajo": miembro.direccion_trabajo,
            "contacto_emergencia_nombre": miembro.contacto_emergencia_nombre,
            "contacto_emergencia_telefono": miembro.contacto_emergencia_telefono,
            "contacto_emergencia_relacion": miembro.contacto_emergencia_relacion,
            "tipo_sangre": miembro.tipo_sangre,
            "alergias": miembro.alergias,
            "condiciones_medicas": miembro.condiciones_medicas,
            "medicamentos": miembro.medicamentos,
            "telefono_secundario": miembro.telefono_secundario,
            "lugar_nacimiento": miembro.lugar_nacimiento,
            "nacionalidad": miembro.nacionalidad,
            "estado_civil": miembro.estado_civil,
            "nivel_educativo": miembro.nivel_educativo,
            "profesion": miembro.profesion,
            "pasaporte": miembro.pasaporte,
            "iglesia_anterior": miembro.iglesia_anterior,
            "fecha_conversion": miembro.fecha_conversion,
            "fecha_bautismo": miembro.fecha_bautismo,
            "fecha_ingreso_iglesia": miembro.fecha_ingreso_iglesia,
        }
        form = SolicitudActualizacionForm(initial=initial, allowed_fields=allowed_fields)

    return render(request, "actualizacion_datos_miembros/formulario_publico.html", {
        "miembro": miembro,
        "acceso": acceso,
        "form": form,
    })


def formulario_ok(request, token):
    acceso = get_object_or_404(AccesoActualizacionDatos, token=token)
    return render(request, "actualizacion_datos_miembros/publico_ok.html", {
        "miembro": acceso.miembro,
    })


# ==========================================================
# ADMIN - SOLICITUDES DE ACTUALIZACIÓN
# ==========================================================
@login_required
def solicitudes_lista(request):
    tenant = _require_tenant(request)
    qs = SolicitudActualizacionMiembro.objects.filter(tenant=tenant).select_related("miembro")

    estado = (request.GET.get("estado") or "").strip()
    if estado:
        qs = qs.filter(estado=estado)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(miembro__nombres__icontains=q) |
            Q(miembro__apellidos__icontains=q) |
            Q(miembro__codigo__icontains=q)
        )

    return render(request, "actualizacion_datos_miembros/solicitudes_lista.html", {
        "solicitudes": qs[:300],
        "estado": estado,
        "q": q,
        "Estados": SolicitudActualizacionMiembro.Estados,
    })


@login_required
def solicitud_detalle(request, pk):
    tenant = _require_tenant(request)
    solicitud = get_object_or_404(
        SolicitudActualizacionMiembro.objects.select_related("miembro"),
        pk=pk,
        tenant=tenant
    )
    ua_legible = traducir_user_agent(solicitud.user_agent)

    return render(request, "actualizacion_datos_miembros/solicitud_detalle.html", {
        "s": solicitud,
        "Estados": SolicitudActualizacionMiembro.Estados,
        "ua_legible": ua_legible,
    })


@login_required
def solicitud_aplicar(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    tenant = _require_tenant(request)
    solicitud = get_object_or_404(
        SolicitudActualizacionMiembro.objects.select_related("miembro"),
        pk=pk,
        tenant=tenant
    )

    if solicitud.estado != SolicitudActualizacionMiembro.Estados.PENDIENTE:
        messages.info(request, "Esta solicitud ya fue procesada.")
        return redirect("actualizacion_datos_miembros:solicitud_detalle", pk=solicitud.pk)

    aplicar_solicitud_a_miembro(solicitud)

    solicitud.estado = SolicitudActualizacionMiembro.Estados.APLICADA
    solicitud.revisado_en = timezone.now()
    solicitud.revisado_por = request.user
    solicitud.save(update_fields=["estado", "revisado_en", "revisado_por"])

    messages.success(request, "Solicitud aplicada: los datos del miembro fueron actualizados.")
    return redirect("actualizacion_datos_miembros:solicitud_detalle", pk=solicitud.pk)


@login_required
def solicitud_rechazar(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    tenant = _require_tenant(request)
    solicitud = get_object_or_404(SolicitudActualizacionMiembro, pk=pk, tenant=tenant)

    if solicitud.estado != SolicitudActualizacionMiembro.Estados.PENDIENTE:
        messages.info(request, "Esta solicitud ya fue procesada.")
        return redirect("actualizacion_datos_miembros:solicitud_detalle", pk=solicitud.pk)

    nota = (request.POST.get("nota_admin") or "").strip()
    solicitud.estado = SolicitudActualizacionMiembro.Estados.RECHAZADA
    solicitud.nota_admin = nota
    solicitud.revisado_en = timezone.now()
    solicitud.revisado_por = request.user
    solicitud.save(update_fields=["estado", "nota_admin", "revisado_en", "revisado_por"])

    messages.success(request, "Solicitud rechazada.")
    return redirect("actualizacion_datos_miembros:solicitud_detalle", pk=solicitud.pk)