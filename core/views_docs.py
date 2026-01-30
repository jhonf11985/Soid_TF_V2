from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import DocumentoCompartido

import urllib.request


def ver_doc_publico(request, token):
    doc = get_object_or_404(DocumentoCompartido, token=token, activo=True)

    # ✅ Expiración
    if doc.expira_en and timezone.now() > doc.expira_en:
        raise Http404("Documento no disponible.")

    if not doc.archivo:
        raise Http404("Documento no disponible.")

    url = doc.archivo.url  # URL real (Cloudinary)

    try:
        # ✅ Descarga el PDF desde Cloudinary
        with urllib.request.urlopen(url, timeout=25) as r:
            data = r.read()
    except Exception:
        raise Http404("Documento no disponible.")

    # ✅ Validación rápida: un PDF real empieza con %PDF
    if not data or not data.startswith(b"%PDF"):
        raise Http404("Documento no disponible.")

    # ✅ Responder con cabeceras correctas para visor PDF
    nombre = (doc.titulo or "documento").replace("/", "-").strip()
    resp = HttpResponse(data, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{nombre}.pdf"'
    return resp
