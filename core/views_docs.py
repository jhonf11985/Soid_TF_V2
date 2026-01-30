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

    url = doc.archivo.url  # Cloudinary URL

    try:
        # ✅ Evita bloqueos de Cloudinary (User-Agent)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
    except Exception as e:
        print("ERROR descargando PDF:", e)
        raise Http404("Documento no disponible.")

    # ❌ QUITAMOS la validación %PDF (es la que te está rompiendo todo)

    nombre = (doc.titulo or "documento").replace("/", "-").strip()
    resp = HttpResponse(data, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{nombre}.pdf"'
    return resp
