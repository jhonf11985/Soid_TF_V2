from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import DocumentoCompartido


def ver_doc_publico(request, token):
    doc = get_object_or_404(DocumentoCompartido, token=token, activo=True)

    # Si tu modelo tiene expiración
    if hasattr(doc, "expira_en") and doc.expira_en and timezone.now() > doc.expira_en:
        raise Http404("Documento no disponible.")

    if not doc.archivo:
        raise Http404("Documento no disponible.")

    try:
        f = doc.archivo.open("rb")
    except Exception:
        raise Http404("Documento no disponible.")

    # ✅ Forzamos cabeceras correctas para visor PDF
    response = FileResponse(f, content_type="application/pdf")
    nombre = (doc.titulo or "documento").replace("/", "-").strip()
    response["Content-Disposition"] = f'inline; filename="{nombre}.pdf"'
    return response
