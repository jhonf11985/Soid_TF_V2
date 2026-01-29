# core/views_docs.py

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from .models import DocumentoCompartido


def ver_doc_publico(request, token):
    """
    Documento público por token: NO requiere login.
    Reglas:
    - activo = True
    - no expirado
    - archivo existente
    """
    doc = get_object_or_404(DocumentoCompartido, token=token)

    if doc.esta_expirado or not doc.archivo:
        raise Http404("Documento no disponible.")

    # Mostrar inline en el navegador (si quieres forzar descarga, lo cambiamos luego)
    response = FileResponse(doc.archivo.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="documento.pdf"'
    return response
