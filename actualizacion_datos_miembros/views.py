from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.urls import reverse
from miembros_app.models import ESTADO_MIEMBRO_CHOICES
from .models import AltaMasivaConfig
from .utils import traducir_user_agent

from miembros_app.models import Miembro
from .models import (
    AccesoActualizacionDatos,
    SolicitudActualizacionMiembro,
    SolicitudAltaMiembro,
)
from .forms import SolicitudActualizacionForm, SolicitudAltaPublicaForm
from .services import aplicar_solicitud_a_miembro, crear_miembro_desde_solicitud_alta
from .services import _normalizar_cedula_rd
from django.db.models import Q
from .models import AltaMasivaConfig
from .models import ActualizacionDatosConfig
from .forms import ActualizacionDatosConfigForm
import re

from django.urls import reverse
from django.utils import timezone
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseForbidden
from miembros_app.models import Miembro
from .models import AccesoAltaFamilia, AltaFamiliaLog
from .services import aplicar_alta_familia




@login_required
def familia_links_lista(request):
    """
    Admin: lista links existentes (sin miembro).
    """
    q = (request.GET.get("q") or "").strip()

    items = AccesoAltaFamilia.objects.all().order_by("-creado_en")
    # Si quieres búsqueda, que sea por token
    if q:
        items = items.filter(token__icontains=q)

    return render(
        request,
        "actualizacion_datos_miembros/link_familias_lista.html",
        {"items": items, "q": q},
    )



@login_required
def familia_generar_link(request):
    """
    Admin: crea un link neutral (sin escoger miembro).
    """
    link = None

    if request.method == "POST":
        acceso = AccesoAltaFamilia.objects.create(activo=True)
        link = request.build_absolute_uri(
            reverse("actualizacion_datos_miembros:familia_formulario_publico", kwargs={"token": acceso.token})
        )
        messages.success(request, "Link creado correctamente.")

    return render(request, "actualizacion_datos_miembros/link_familias.html", {"link": link})


@login_required
def familia_alertas(request):
    """
    Admin: muestra alertas/conflictos detectados en solicitudes de familia.
    Las alertas se extraen del campo JSONField 'alertas' de AltaFamiliaLog.
    """
    tipo_filtro = (request.GET.get("tipo") or "").strip().lower()

    # Obtener todos los logs que tienen alertas
    logs_con_alertas = AltaFamiliaLog.objects.filter(
        alertas__isnull=False
    ).exclude(
        alertas=[]
    ).select_related("principal").order_by("-creado_en")

    # Construir lista de alertas con contexto
    alertas = []
    for log in logs_con_alertas:
        for alerta_data in log.alertas:
            # Normalizar la alerta (puede ser string o dict)
            if isinstance(alerta_data, str):
                alerta = {
                    "mensaje": alerta_data,
                    "tipo": "conflicto",
                    "nivel": "warning",
                }
            else:
                alerta = {
                    "mensaje": alerta_data.get("motivo") or alerta_data.get("mensaje") or str(alerta_data),
                    "tipo": alerta_data.get("tipo", "conflicto"),
                    "nivel": alerta_data.get("nivel", "warning"),
                }

            # Agregar contexto
            alerta["principal"] = log.principal
            alerta["solicitud_id"] = log.pk
            alerta["fecha"] = log.creado_en

            # Filtrar por tipo si se especificó
            if tipo_filtro and alerta["tipo"].lower() != tipo_filtro:
                continue

            alertas.append(alerta)

    # Calcular estadísticas
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


from django.http import JsonResponse
from django.db.models import Q

from .models import AccesoAltaFamilia
from miembros_app.models import Miembro


def api_buscar_miembros(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"success": True, "resultados": []})

    # Seguridad opcional: si viene token, exigimos que sea válido/activo.
    token = (request.GET.get("token") or "").strip()
    if token:
        if not AccesoAltaFamilia.objects.filter(token=token, activo=True).exists():
            # No exponemos info: simplemente devolvemos vacío
            return JsonResponse({"success": True, "resultados": []})

    # Parámetros opcionales (tu JS manda filtro y limit) :contentReference[oaicite:1]{index=1}
    filtro = (request.GET.get("filtro") or "").strip().lower()
    try:
        limit = int(request.GET.get("limit") or 15)
    except ValueError:
        limit = 15
    limit = max(1, min(limit, 25))  # límite duro para evitar abuso

    qs = Miembro.objects.filter(
        Q(nombres__icontains=q) |
        Q(apellidos__icontains=q) |
        Q(cedula__icontains=q)
    )

    # Si tienes campo estado/activo, aplica el filtro aquí
    # (no lo fuerzo porque no sé tus nombres exactos)
    if filtro in ("activo", "activos"):
        if hasattr(Miembro, "activo"):
            qs = qs.filter(activo=True)
        elif hasattr(Miembro, "estado"):
            # si tienes estados tipo "ACTIVO"
            qs = qs.filter(estado__iexact="ACTIVO")

    qs = qs.order_by("nombres", "apellidos")[:limit]

    resultados = []
    for m in qs:
        nombre = f"{m.nombres} {m.apellidos}".strip()
        resultados.append({
            "id": m.id,
            "nombre": nombre,
            # tu autocomplete muestra "codigo" si existe :contentReference[oaicite:2]{index=2}
            "codigo": getattr(m, "codigo", "") or getattr(m, "numero_miembro", "") or "",
            # teléfono opcional
            "telefono": getattr(m, "telefono", "") or "—",
            # NO es necesario mandar cédula aquí (y es más sensible), pero si la quieres:
            # "cedula": getattr(m, "cedula", "") or "",
        })

    return JsonResponse({"success": True, "resultados": resultados})

@login_required
def generar_link_familia(request, miembro_id):
    jefe = get_object_or_404(Miembro, pk=miembro_id)

    acceso, created = AccesoAltaFamilia.objects.get_or_create(jefe=jefe)
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
# ============================================
# REEMPLAZAR familia_formulario_publico en views.py
# ============================================

def familia_formulario_publico(request, token):
    """
    Público: Pantalla bienvenida + seleccionar principal + construir familia.
    Solo guarda la solicitud como PENDIENTE, NO aplica relaciones.
    El admin debe aprobar para que se apliquen.
    """
    acceso = get_object_or_404(AccesoAltaFamilia, token=token, activo=True)

    # IMPORTANTE: aquí tú ya tienes CFG en otros formularios.
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
            principal = Miembro.objects.get(id=int(principal_id))
        except (Miembro.DoesNotExist, ValueError):
            messages.error(request, "El miembro principal seleccionado no es válido.")
            return render(request, "actualizacion_datos_miembros/familia_publico.html", {"CFG": CFG, "acceso": acceso})

        # Normalizar IDs opcionales
        conyuge_id_int = int(conyuge_id) if conyuge_id else None
        padre_id_int = int(padre_id) if padre_id else None
        madre_id_int = int(madre_id) if madre_id else None
        hijos_ids_int = []
        for x in hijos_ids:
            x = (x or "").strip()
            if not x:
                continue
            try:
                hijos_ids_int.append(int(x))
            except ValueError:
                continue

        # Obtener IP y User Agent para auditoría
        ip_origen = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
        if ip_origen and "," in ip_origen:
            ip_origen = ip_origen.split(",")[0].strip()
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]

        # Crear solicitud como PENDIENTE (NO aplicar relaciones aún)
        AltaFamiliaLog.objects.create(
            acceso=acceso,
            principal=principal,
            conyuge_id=conyuge_id_int,
            padre_id=padre_id_int,
            madre_id=madre_id_int,
            hijos_ids=hijos_ids_int,
            estado="pendiente",  # <-- IMPORTANTE: estado pendiente
            ip_origen=ip_origen,
            user_agent=user_agent,
        )

        # Marcar último envío
        acceso.ultimo_envio_en = timezone.now()
        acceso.save(update_fields=["ultimo_envio_en", "actualizado_en"])

        return render(
            request,
            "actualizacion_datos_miembros/familia_ok.html",
            {"CFG": CFG, "principal": principal},
        )

    return render(request, "actualizacion_datos_miembros/familia_publico.html", {"CFG": CFG, "acceso": acceso})

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

            # Si lo dejan vacío, no lo borramos (mantenemos el actual)
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

    return render(
        request,
        "actualizacion_datos_miembros/alta_masiva_link.html",
        {
            "link": link,
            "public_url": link,
            "config": config,
            "Estados": SolicitudActualizacionMiembro.Estados,
            "EstadosAlta": SolicitudAltaMiembro.Estados,
        },
    )



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
            cedula = _normalizar_cedula_rd(form.cleaned_data.get("cedula") or "")

            # Normalizar cédula a formato 000-0000000-0 si hay 11 dígitos
            ced_norm = _normalizar_cedula_rd(cedula)
            ced_digits = re.sub(r"\D", "", (cedula or "").strip())



            
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
    ua_legible = traducir_user_agent(s.user_agent)

    return render(request, "actualizacion_datos_miembros/solicitud_detalle.html", {
        "s": solicitud,
        "Estados": SolicitudActualizacionMiembro.Estados,
        "ua_legible": ua_legible,
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


# ============================================
# REEMPLAZAR familia_solicitudes_lista en views.py
# ============================================

@login_required
def familia_solicitudes_lista(request):
    """
    Admin: lista de solicitudes de alta de familia.
    """
    # Obtener todas las solicitudes
    qs_all = AltaFamiliaLog.objects.select_related("principal", "acceso").order_by("-creado_en")

    # Contadores para los stats cards
    total_count = qs_all.count()
    pendientes_count = qs_all.filter(estado="pendiente").count()
    aplicadas_count = qs_all.filter(estado="aplicada").count()
    rechazadas_count = qs_all.filter(estado="rechazada").count()

    # Aplicar filtro de estado si existe
    qs = qs_all
    estado = (request.GET.get("estado") or "").strip()
    if estado:
        qs = qs.filter(estado=estado)

    # Aplicar filtro de búsqueda
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
    """
    Admin: detalle de una solicitud de familia.
    """
    s = get_object_or_404(AltaFamiliaLog.objects.select_related("principal", "acceso"), pk=pk)

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
    """
    Admin: aplicar la solicitud de familia (crear relaciones).
    """
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    s = get_object_or_404(AltaFamiliaLog, pk=pk)

    if s.estado != AltaFamiliaLog.Estados.PENDIENTE:
        messages.info(request, "Esta solicitud ya fue procesada.")
        return redirect("actualizacion_datos_miembros:familia_solicitud_detalle", pk=s.pk)

    # Aplicar las relaciones
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

    # Marcar como aplicada
    s.estado = AltaFamiliaLog.Estados.APLICADA
    s.revisado_en = timezone.now()
    s.revisado_por = request.user
    s.save()

    messages.success(request, "Solicitud aplicada ✅ Las relaciones familiares fueron creadas.")
    return redirect("actualizacion_datos_miembros:familia_solicitud_detalle", pk=s.pk)


@login_required
def familia_solicitud_rechazar(request, pk):
    """
    Admin: rechazar la solicitud de familia.
    """
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    s = get_object_or_404(AltaFamiliaLog, pk=pk)

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
