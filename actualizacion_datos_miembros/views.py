from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.urls import reverse
from miembros_app.models import ESTADO_MIEMBRO_CHOICES
from .models import AltaMasivaConfig

from miembros_app.models import Miembro
from .models import (
    AccesoActualizacionDatos,
    SolicitudActualizacionMiembro,
    SolicitudAltaMiembro,
)
from .forms import SolicitudActualizacionForm, SolicitudAltaPublicaForm
from .services import aplicar_solicitud_a_miembro, crear_miembro_desde_solicitud_alta

from django.db.models import Q
from .models import AltaMasivaConfig
from .models import ActualizacionDatosConfig
from .forms import ActualizacionDatosConfigForm

@login_required
def actualizacion_config(request):
    config = ActualizacionDatosConfig.get_solo()

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




def limpiar_cedula(value):
    return (value or "").replace("-", "").replace(" ", "")


@login_required
def alta_masiva_config(request):
    config = AltaMasivaConfig.get_solo()

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
        # para que tu sidebar no se rompa si usa Estados/EstadosAlta
        "Estados": SolicitudActualizacionMiembro.Estados,
        "EstadosAlta": SolicitudAltaMiembro.Estados,
    })

@login_required
def alta_masiva_link(request):
    config = AltaMasivaConfig.get_solo()

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()
        if accion == "abrir":
            config.activo = True
        elif accion == "cerrar":
            config.activo = False
        config.save(update_fields=["activo", "actualizado_en"])

        messages.success(
            request,
            "Alta masiva ACTIVADA." if config.activo else "Alta masiva CERRADA."
        )
        return redirect("actualizacion_datos_miembros:alta_masiva_link")

    link = request.build_absolute_uri(reverse("actualizacion_datos_miembros:alta_publica"))

    return render(request, "actualizacion_datos_miembros/alta_masiva_link.html", {
        "link": link,
        "public_url": link,
        "config": config,
        "Estados": SolicitudActualizacionMiembro.Estados,
        "EstadosAlta": SolicitudAltaMiembro.Estados,
    })


@login_required
def links_lista(request):
    q = (request.GET.get("q") or "").strip()

    qs = (
        Miembro.objects
        .all()
        .select_related("acceso_actualizacion_datos")  # related_name del OneToOne
        .order_by("apellidos", "nombres")
    )

    if q:
        qs = qs.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(codigo__icontains=q)
            | Q(telefono__icontains=q)
        )

    return render(request, "actualizacion_datos_miembros/links_lista.html", {
        "miembros": qs[:300],
        "q": q,
        # Para que el sidebar (y otras pantallas) sigan usando Estados sin romperse
        "Estados": SolicitudActualizacionMiembro.Estados,
        "EstadosAlta": SolicitudAltaMiembro.Estados,
    })
@login_required
def altas_aprobar_masivo(request):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    ids_str = request.POST.get("ids", "")
    if not ids_str:
        messages.warning(request, "No se seleccionaron solicitudes.")
        return redirect("actualizacion_datos_miembros:altas_lista")

    ids = [int(i) for i in ids_str.split(",") if i.strip().isdigit()]

    solicitudes = SolicitudAltaMiembro.objects.filter(
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

    ids_str = request.POST.get("ids", "")
    if not ids_str:
        messages.warning(request, "No se seleccionaron solicitudes.")
        return redirect("actualizacion_datos_miembros:altas_lista")

    ids = [int(i) for i in ids_str.split(",") if i.strip().isdigit()]
    nota = (request.POST.get("nota_admin") or "").strip()

    solicitudes = SolicitudAltaMiembro.objects.filter(
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

    s = get_object_or_404(SolicitudAltaMiembro, pk=pk)

    if s.estado != SolicitudAltaMiembro.Estados.PENDIENTE:
        messages.info(request, "No se puede modificar una solicitud ya procesada.")
        return redirect("actualizacion_datos_miembros:altas_lista")

    nuevo_estado = (request.POST.get("estado_miembro") or "").strip()

    # Validar contra choices
    estados_validos = [c[0] for c in ESTADO_MIEMBRO_CHOICES]
    if nuevo_estado not in estados_validos:
        messages.error(request, "Estado de miembro inválido.")
        return redirect("actualizacion_datos_miembros:altas_lista")

    s.estado_miembro = nuevo_estado
    s.save(update_fields=["estado_miembro"])

    messages.success(request, "Estado del miembro actualizado.")
    return redirect("actualizacion_datos_miembros:altas_lista")


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
    config = AltaMasivaConfig.get_solo()
    if not config.activo:
        return render(request, "actualizacion_datos_miembros/alta_cerrada.html", {})

    if request.method == "POST":
        form = SolicitudAltaPublicaForm(
            request.POST,
            request.FILES   # 👈 IMPRESCINDIBLE para fotos
        )

        if form.is_valid():
            tel = (form.cleaned_data.get("telefono") or "").strip()
            cedula = limpiar_cedula(form.cleaned_data.get("cedula"))


            
                        # Anti-duplicado: si ya existe una solicitud pendiente con ese teléfono
            if SolicitudAltaMiembro.objects.filter(
                telefono=tel,
                estado=SolicitudAltaMiembro.Estados.PENDIENTE
            ).exists():
                # Mostrar el error EN EL MISMO FORMULARIO (no redirigir)
                form.add_error(
                    "telefono",
                    "Este teléfono ya tiene una solicitud pendiente. Si ya la enviaste, espera la revisión del equipo."
                )
                # Opcional: también puedes ponerlo como error general (arriba)
                # form.add_error(None, "Ya existe una solicitud pendiente con este teléfono.")
                return render(request, "actualizacion_datos_miembros/alta_publico.html", {"form": form})
         

            import re

            digits = re.sub(r"\D+", "", tel)

            # Si viene como +1XXXXXXXXXX, quitamos el 1
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]

            tel_norm = digits[:10] if len(digits) >= 10 else ""

            if tel_norm and Miembro.objects.filter(telefono_norm=tel_norm).exists():
                form.add_error(
                    "telefono",
                    "Este teléfono ya está registrado en el sistema. "
                    "Si necesitas actualizar datos, solicita el enlace de actualización."
                )
                return render(
                    request,
                    "actualizacion_datos_miembros/alta_publico.html",
                    {"form": form}
                )

            # Anti-duplicado por cédula (solo si fue enviada)
            if cedula:
                if SolicitudAltaMiembro.objects.filter(
                    cedula=cedula,
                    estado=SolicitudAltaMiembro.Estados.PENDIENTE
                ).exists():
                    form.add_error(
                        "cedula",
                        "Esta cédula ya tiene una solicitud pendiente. Si ya la enviaste, espera la revisión del equipo."
                    )
                    return render(
                        request,
                        "actualizacion_datos_miembros/alta_publico.html",
                        {"form": form}
                    )

            if cedula and Miembro.objects.filter(cedula=cedula).exists():
                form.add_error(
                    "cedula",
                    "Esta cédula ya está registrada en el sistema. Si necesitas actualizar datos, solicita el enlace de actualización."
                )
                return render(
                    request,
                    "actualizacion_datos_miembros/alta_publico.html",
                    {"form": form}
                )
            solicitud = form.save(commit=False)
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

    return render(request, "actualizacion_datos_miembros/alta_publico.html", {
        "form": form
    })


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

    config = ActualizacionDatosConfig.get_solo()
    if not config.activo:
        # Si quieres, puedes reutilizar publico_inactivo o hacer una pantalla nueva.
        return render(request, "actualizacion_datos_miembros/publico_inactivo.html", {
            "miembro": acceso.miembro,
        })

    allowed_fields = config.campos_permitidos or None


    if request.method == "POST":
        form = SolicitudActualizacionForm(request.POST, allowed_fields=allowed_fields)

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
            

            # 🔒 Desactivar el link después de enviar
            acceso.ultimo_envio_en = timezone.now()
            acceso.activo = False
            acceso.save(update_fields=["ultimo_envio_en", "activo", "actualizado_en"])


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

                        # AGREGAR ESTOS NUEVOS:
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
        "estado_miembro_choices": ESTADO_MIEMBRO_CHOICES,
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

    # 1) Crear el miembro primero (si falla por duplicado, no aprobamos)
    try:
        miembro = crear_miembro_desde_solicitud_alta(s)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect("actualizacion_datos_miembros:alta_detalle", pk=s.pk)

    # 2) Marcar la solicitud como aprobada
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
