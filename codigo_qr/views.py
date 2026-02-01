from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from .models import QrToken, QrScanLog


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
