from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.urls import reverse

from miembros_app.models import Miembro
from .models import AccesoActualizacionDatos, SolicitudActualizacionMiembro
from .forms import SolicitudActualizacionForm
from .services import aplicar_solicitud_a_miembro
from .forms import SolicitudActualizacionForm


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def formulario_publico(request, token):
    acceso = get_object_or_404(AccesoActualizacionDatos, token=token)

    if not acceso.activo:
        return render(request, "actualizacion_datos_miembros/publico_inactivo.html", {
            "miembro": acceso.miembro,
        })

    miembro = acceso.miembro

    if request.method == "POST":
        form = SolicitudActualizacionForm(request.POST)
        if form.is_valid():
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

    return render(request, "actualizacion_datos_miembros/link_miembro.html", {
        "miembro": miembro,
        "acceso": acceso,
        "link": link,
        "created": created,
    })




def public_registro(request):
    if request.method == "POST":
        form = formulario_publico(request.POST)
        if form.is_valid():
            SolicitudActualizacion.objects.create(
                tipo=SolicitudActualizacion.Tipos.ALTA,
                estado=SolicitudActualizacion.Estados.PENDIENTE,
                payload=form.cleaned_data,
                enviado_en=timezone.now(),
            )
            return render(request, "actualizacion_datos_miembros/public_ok.html")
    else:
        form = formulario_publico()

    return render(request, "actualizacion_datos_miembros/formulario_publico.html", {
        "form": form,
        "modo": "ALTA",
    })