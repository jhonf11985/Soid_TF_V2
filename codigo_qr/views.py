from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from .models import QrToken, QrScanLog
import io
import qrcode
from .services import generar_token
from django.http import HttpResponse
from django.urls import reverse
from miembros_app.models import Miembro
from django.shortcuts import get_object_or_404, redirect



def qr_scan(request):
    return render(request, "codigo_qr/scan.html")


def qr_resolver(request, token: str):
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
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


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

def qr_por_miembro(request, miembro_id: int):
    miembro = get_object_or_404(Miembro, id=miembro_id)

    qr, creado = QrToken.objects.get_or_create(
        miembro=miembro,
        defaults={"token": generar_token(), "activo": True},
    )

    # Si existe pero no tiene token (caso raro), lo arreglamos
    if not qr.token:
        qr.token = generar_token()
        qr.save(update_fields=["token"])

    # Reutilizamos la misma pantalla detalle que ya tienes
    return render(request, "codigo_qr/detalle.html", {"qr": qr, "resultado": "ok"})
