from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.urls import reverse

from miembros_app.models import Miembro
from .models import (
    AccesoActualizacionDatos,
    SolicitudActualizacionMiembro,
    SolicitudAltaMiembro,
)
from .forms import SolicitudActualizacionForm, PublicRegistroAltaForm
from .services import aplicar_solicitud_a_miembro


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ==========================================================
# PÚBLICO - ALTA MASIVA
# ==========================================================
def alta_publica(request):
    """
    Formulario público para registro (alta masiva).
    Crea SolicitudAltaMiembro (NO crea Miembro directo).
    """
    if request.method == "POST":
        form = PublicRegistroAltaForm(request.POST)
        if form.is_valid():
            # Anti-duplicado simple: si hay una pendiente con ese teléfono, no crear otra.
            tel = (form.cleaned_data.get("telefono") or "").strip()
            if SolicitudAltaMiembro.objects.filter(
                telefono=tel,
                estado=SolicitudAltaMiembro.Estados.PENDIENTE
            ).exists():
                messages.info(
                    request,
                    "Ya existe una solicitud pendiente con este teléfono. El equipo la revisará pronto."
                )
                return redirect("actualizacion_datos_miembros:alta_ok")

            SolicitudAltaMiembro.objects.create(
                estado=SolicitudAltaMiembro.Estados.PENDIENTE,
                nombres=form.cleaned_data["nombres"],
                apellidos=form.cleaned_data["apellidos"],
                genero=form.cleaned_data["genero"],
                fecha_nacimiento=form.cleaned_data["fecha_nacimiento"],
                estado_miembro=form.cleaned_data["estado_miembro"],
                telefono=tel,
                ip_origen=_get_client_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
            )
            return redirect("actualizacion_datos_miembros:alta_ok")
        else:
            messages.error(request, "Revisa los campos marcados. Hay errores en el formulario.")
    else:
        form = PublicRegistroAltaForm()

    return render(request, "actualizacion_datos_miembros/alta_publico.html", {"form": form})


def alta_ok(request):
    return render(request, "actualizacion_datos_miembros/alta_ok.html")


# ==========================================================
# PÚBLICO - ACTUALIZACIÓN (ya existente, renombrado limpio)
# ==========================================================
def formulario_actualizacion_publico(request, token):
    acceso = get_object_or_404(AccesoActualizacionDatos, token=token)

    if not acceso.activo:
        return render(request, "actualizacion_datos_miembros/publico_inactivo.html", {
            "miembro": acceso.miembro,
        })

    miembro = acceso.miembro

    if request.method == "POST":
        form = SolicitudActualizacionForm(request.POST)
        if form.is_valid():
            # Evitar spam: si ya hay una solicitud pendiente, no crear otra
            if SolicitudActualizacionMiembro.objects.filter(
                miembro=miembro,
                estado=SolicitudActualizacionMiembro.Estados.PENDIENTE
            ).exists():
                messages.info(
                    request,
                    "Ya tienes una solicitud pendiente. El equipo la revisará pronto."
                )
                return redirect("actualizacion_datos_miembros:formulario_ok", token=acceso.token)

            solicitud = form.save(commit=False)
            solicitud.miembro = miembro
            solicitud.estado = SolicitudActualizacionMiembro.Estados.PENDIENTE
            solicitud.ip_origen = _get_client_ip(request)
            solicitud.user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:255]
            solicitud.save()

            acceso.ultimo_envio_en = timezone.now()
            acceso.save(update_fields=["ultimo_envio_en", "actualizado_en"])

            return redirect("actualizacion_datos_miembros:formulario_ok", token=acceso.token)
        else:
            messages.error(request, "Revisa los campos marcados. Hay errores en el formulario.")
    else:
        # Prellenar con datos actuales del miembro
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
        }
        form = SolicitudActualizacionForm(initial=initial)

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
# ADMIN - ACTUALIZACIÓN
# ==========================================================
@login_required
def solicitudes_lista(request):
    qs = (
        SolicitudActualizacionMiembro.objects
        .select_related("miembro")
        .all()
    )

    estado = (request.GET.get("estado") or "").strip()
    if estado:
        qs = qs.filter(estado=estado)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            miembro__nombres__icontains=q
        ) | qs.filter(
            miembro__apellidos__icontains=q
        ) | qs.filter(
            miembro__codigo__icontains=q
        )

    return render(request, "actualizacion_datos_miembros/solicitudes_lista.html", {
        "solicitudes": qs[:300],
        "estado": estado,
        "q": q,
        "Estados": SolicitudActualizacionMiembro.Estados,
    })


@login_required
def solicitud_detalle(request, pk):
    solicitud = get_object_or_404(
        SolicitudActualizacionMiembro.objects.select_related("miembro"),
        pk=pk
    )
    return render(request, "actualizacion_datos_miembros/solicitud_detalle.html", {
        "s": solicitud,
        "Estados": SolicitudActualizacionMiembro.Estados,
    })


@login_required
def solicitud_aplicar(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    solicitud = get_object_or_404(
        SolicitudActualizacionMiembro.objects.select_related("miembro"),
        pk=pk
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

    solicitud = get_object_or_404(SolicitudActualizacionMiembro, pk=pk)

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


@login_required
def generar_link_miembro(request, miembro_id):
    miembro = get_object_or_404(Miembro, pk=miembro_id)

    acceso, created = AccesoActualizacionDatos.objects.get_or_create(miembro=miembro)
    if not acceso.activo:
        acceso.activo = True
        acceso.save(update_fields=["activo", "actualizado_en"])

    link = request.build_absolute_uri(
        reverse("actualizacion_datos_miembros:formulario_publico", kwargs={"token": acceso.token})
    )

    # OJO: tu template actual usa public_url; aquí mandamos ambas por compatibilidad.
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
    qs = SolicitudAltaMiembro.objects.all()

    estado = (request.GET.get("estado") or "").strip()
    if estado:
        qs = qs.filter(estado=estado)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            nombres__icontains=q
        ) | qs.filter(
            apellidos__icontains=q
        ) | qs.filter(
            telefono__icontains=q
        )

    return render(request, "actualizacion_datos_miembros/altas_lista.html", {
        "altas": qs[:300],
        "estado": estado,
        "q": q,
        "Estados": SolicitudAltaMiembro.Estados,
    })


@login_required
def alta_detalle(request, pk):
    s = get_object_or_404(SolicitudAltaMiembro, pk=pk)
    return render(request, "actualizacion_datos_miembros/alta_detalle.html", {
        "s": s,
        "Estados": SolicitudAltaMiembro.Estados,
    })


@login_required
def alta_aprobar(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    s = get_object_or_404(SolicitudAltaMiembro, pk=pk)
    if s.estado != SolicitudAltaMiembro.Estados.PENDIENTE:
        messages.info(request, "Esta solicitud ya fue procesada.")
        return redirect("actualizacion_datos_miembros:alta_detalle", pk=s.pk)

    s.estado = SolicitudAltaMiembro.Estados.APROBADA
    s.revisado_en = timezone.now()
    s.revisado_por = request.user
    s.save(update_fields=["estado", "revisado_en", "revisado_por"])

    messages.success(request, "Solicitud aprobada. (Más adelante la convertiremos en Miembro automáticamente).")
    return redirect("actualizacion_datos_miembros:alta_detalle", pk=s.pk)


@login_required
def alta_rechazar(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    s = get_object_or_404(SolicitudAltaMiembro, pk=pk)
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
