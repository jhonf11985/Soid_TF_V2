from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from core.models import DocumentoCompartido


def ver_doc_publico(request, token):
    doc = get_object_or_404(DocumentoCompartido, token=token, activo=True)

    if doc.expira_en and timezone.now() > doc.expira_en:
        raise Http404("Documento no disponible.")

    if not doc.archivo:
        raise Http404("Documento no disponible.")

    return redirect(doc.archivo.url)
