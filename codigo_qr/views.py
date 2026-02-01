from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.urls import reverse
from django.db.models import Q

import io
import re
import qrcode
from urllib.parse import quote

from .models import QrToken, QrScanLog, QrEnvio
from .services import generar_token
from miembros_app.models import Miembro


# ═══════════════════════════════════════════════════════════════════════════════
# VISTAS DE ESCANEO QR
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
def qr_scan(request):
    """Página para escanear códigos QR."""
    return render(request, "codigo_qr/scan.html")


@require_GET
def qr_resolver(request, token: str):
    """
    Resuelve un token QR y registra el escaneo.
    Pública para que cualquiera pueda escanear.
    """
    try:
        qr = QrToken.objects.get(token=token)
    except QrToken.DoesNotExist:
        raise Http404("QR inválido")

    resultado = "ok"
    if not qr.activo:
        resultado = "inactivo"
    elif qr.expira_en and timezone.now() > qr.expira_en:
        resultado = "expirado"

    QrScanLog.objects.create(
        token=qr,
        escaneado_por=request.user if request.user.is_authenticated else None,
        modo=request.GET.get("modo", "general"),
        resultado=resultado,
        ip=_get_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
    )

    return render(request, "codigo_qr/detalle.html", {"qr": qr, "resultado": resultado})


def _get_ip(request):
    """Obtiene la IP real del cliente."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@login_required
@require_GET
def qr_imagen(request, token: str):
    """
    Devuelve un PNG con el QR apuntando al resolver del token.
    """
    try:
        qr = QrToken.objects.get(token=token)
    except QrToken.DoesNotExist:
        raise Http404("QR inválido")

    destino = request.build_absolute_uri(reverse("codigo_qr:resolver", args=[qr.token]))

    img = qrcode.make(destino)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return HttpResponse(buffer.getvalue(), content_type="image/png")


@login_required
@require_GET
def qr_por_miembro(request, miembro_id: int):
    """
    Muestra/genera el QR de un miembro específico.
    """
    miembro = get_object_or_404(Miembro, id=miembro_id)

    qr, creado = QrToken.objects.get_or_create(
        miembro=miembro,
        defaults={"token": generar_token(), "activo": True},
    )

    if not qr.token:
        qr.token = generar_token()
        qr.save(update_fields=["token"])

    return render(request, "codigo_qr/detalle.html", {"qr": qr, "resultado": "ok"})


# ═══════════════════════════════════════════════════════════════════════════════
# VISTAS DE ENVÍO POR WHATSAPP
# ═══════════════════════════════════════════════════════════════════════════════

def _get_whatsapp(miembro) -> str:
    """
    Obtiene el número de WhatsApp del miembro.
    Ajusta el campo según tu modelo: whatsapp, telefono, celular, etc.
    """
    return (getattr(miembro, "whatsapp", "") or "").strip()


def _normalizar_telefono_whatsapp(tel: str) -> str:
    """
    Devuelve el teléfono solo con dígitos, listo para wa.me
    Regla para RD:
    - Si son 10 dígitos (809XXXXXXX), le antepone 1 -> 1809XXXXXXX
    - Si ya viene con 11+ dígitos, lo deja como está.
    """
    tel = (tel or "").strip()
    dig = re.sub(r"\D+", "", tel)

    # RD típico: 10 dígitos (809/829/849 + 7 dígitos)
    if len(dig) == 10:
        dig = "1" + dig

    return dig


@login_required
@require_GET
def envios_home(request):
    """
    Lista de miembros CON WHATSAPP para seleccionar y poner en cola el envío de su QR.
    """
    q = (request.GET.get("q") or "").strip()

    # ✅ SOLO miembros que tienen WhatsApp (no vacío, no nulo)
    miembros = Miembro.objects.exclude(
        Q(whatsapp__isnull=True) | Q(whatsapp="")
    ).order_by("nombres", "apellidos")

    # Búsqueda por ID o nombre
    if q:
        if q.isdigit():
            miembros = miembros.filter(id=q)
        else:
            miembros = miembros.filter(
                Q(nombres__icontains=q) | 
                Q(apellidos__icontains=q)
            )

    # Excluir los que ya tienen envío pendiente
    ids_pendientes = QrEnvio.objects.filter(
        estado=QrEnvio.ESTADO_PENDIENTE
    ).values_list("miembro_id", flat=True)
    
    miembros = miembros.exclude(id__in=ids_pendientes)

    context = {
        "miembros": miembros[:200],
        "q": q,
        "total_con_whatsapp": miembros.count(),
    }
    return render(request, "codigo_qr/envios_home.html", context)


@login_required
@require_POST
def envios_crear_lote(request):
    """
    Crea QRToken y QrEnvio en estado pendiente para miembros seleccionados.
    """
    ids = request.POST.getlist("miembro_ids")
    ids = [int(x) for x in ids if str(x).isdigit()]

    if not ids:
        messages.warning(request, "No seleccionaste miembros.")
        return redirect("codigo_qr:envios_home")

    miembros = Miembro.objects.filter(id__in=ids)

    creados = 0
    ya_pendientes = 0

    for m in miembros:
        # Crear o obtener el QR Token
        qr, _ = QrToken.objects.get_or_create(
            miembro=m,
            defaults={"token": generar_token(), "activo": True},
        )
        if not qr.token:
            qr.token = generar_token()
            qr.save(update_fields=["token"])

        tel = _get_whatsapp(m)
        
        # Si no tiene WhatsApp, saltamos (no debería pasar si filtramos bien)
        if not tel:
            continue

        # Evitar duplicar pendientes
        existe_pendiente = QrEnvio.objects.filter(
            miembro=m, 
            estado=QrEnvio.ESTADO_PENDIENTE
        ).exists()
        
        if existe_pendiente:
            ya_pendientes += 1
            continue

        # Crear el enlace y mensaje
        link = request.build_absolute_uri(reverse("codigo_qr:por_miembro", args=[m.id]))
        mensaje = f"Hola {m.nombres}, este es tu código QR de la iglesia. Guárdalo o preséntalo cuando se te pida: {link}"

        QrEnvio.objects.create(
            miembro=m,
            token=qr,
            telefono=tel,
            mensaje=mensaje,
            estado=QrEnvio.ESTADO_PENDIENTE,
            creado_por=request.user,
        )
        creados += 1

    if creados > 0:
        messages.success(request, f"✅ {creados} envío(s) agregados a la cola.")
    if ya_pendientes > 0:
        messages.info(request, f"ℹ️ {ya_pendientes} ya estaban en la cola.")
    if creados == 0 and ya_pendientes == 0:
        messages.warning(request, "No se crearon envíos.")

    return redirect("codigo_qr:envios_pendientes")


@login_required
@require_GET
def envios_pendientes(request):
    """
    Lista de envíos pendientes para procesar.
    """
    pendientes = QrEnvio.objects.select_related("miembro", "token").filter(
        estado=QrEnvio.ESTADO_PENDIENTE
    ).order_by("creado_en")

    # Estadísticas
    total_enviados = QrEnvio.objects.filter(estado=QrEnvio.ESTADO_ENVIADO).count()

    return render(
        request,
        "codigo_qr/envios_pendientes.html",
        {
            "pendientes": pendientes[:200],
            "total_pendientes": pendientes.count(),
            "total_enviados": total_enviados,
        },
    )


@login_required
@require_GET
def envios_enviar(request, envio_id: int):
    """
    Abre WhatsApp con el mensaje listo para enviar (wa.me).
    """
    envio = get_object_or_404(QrEnvio, id=envio_id)

    if envio.estado != QrEnvio.ESTADO_PENDIENTE:
        messages.warning(request, "Este envío ya no está pendiente.")
        return redirect("codigo_qr:envios_pendientes")

    tel = (envio.telefono or "").strip()
    tel_norm = _normalizar_telefono_whatsapp(tel)

    if not tel_norm:
        messages.warning(request, "Este miembro no tiene teléfono válido para WhatsApp.")
        return redirect("codigo_qr:envios_pendientes")

    texto = (envio.mensaje or "").strip()
    if not texto:
        link = request.build_absolute_uri(reverse("codigo_qr:por_miembro", args=[envio.miembro.id]))
        texto = f"Hola, este es tu código QR de la iglesia: {link}"

    url = f"https://wa.me/{tel_norm}?text={quote(texto)}"
    return redirect(url)


@login_required
@require_POST
def envios_marcar_enviado(request, envio_id: int):
    """
    Marca el envío como ENVIADO.
    """
    envio = get_object_or_404(QrEnvio, id=envio_id)

    envio.estado = QrEnvio.ESTADO_ENVIADO

    if hasattr(envio, "enviado_en"):
        envio.enviado_en = timezone.now()
    if hasattr(envio, "enviado_por_id") and request.user.is_authenticated:
        envio.enviado_por = request.user

    envio.save()
    messages.success(request, "✅ Envío marcado como enviado.")
    return redirect("codigo_qr:envios_pendientes")

@login_required
@require_GET
def envio_desde_detalle(request, token: str):
    """
    Desde el detalle del QR:
    - Valida que el QR tenga miembro
    - Crea (si no existe) un QrEnvio PENDIENTE
    - Redirige a envios_enviar (que abre WhatsApp wa.me)
    """
    qr = get_object_or_404(QrToken, token=token)

    if not qr.miembro_id:
        messages.warning(request, "Este QR no está asignado a ningún miembro.")
        return redirect("codigo_qr:scan")

    miembro = qr.miembro

    tel = _get_whatsapp(miembro)
    tel_norm = _normalizar_telefono_whatsapp(tel)

    if not tel_norm:
        messages.warning(request, "Este miembro no tiene un WhatsApp válido.")
        return redirect("codigo_qr:por_miembro", miembro.id)

    # Si ya hay un envío pendiente para este miembro + este QR, reutilízalo
    envio = QrEnvio.objects.filter(
        miembro_id=miembro.id,
        token_id=qr.id,
        estado=QrEnvio.ESTADO_PENDIENTE
    ).order_by("-creado_en").first()

    if not envio:
        link = request.build_absolute_uri(reverse("codigo_qr:por_miembro", args=[miembro.id]))
        mensaje = f"Hola {miembro.nombres}, este es tu código QR de la iglesia. Guárdalo o preséntalo cuando se te pida: {link}"

        envio = QrEnvio.objects.create(
            miembro=miembro,
            token=qr,
            telefono=tel,
            mensaje=mensaje,
            estado=QrEnvio.ESTADO_PENDIENTE,
            creado_por=request.user,
        )

    return redirect("codigo_qr:envios_enviar", envio.id)
