from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

def ver_doc_publico(request, token):
    """
    Documento público por token: NO requiere login.
    Reglas:
    - activo = True
    - no expirado
    - archivo existente
    """
    doc = get_object_or_404(DocumentoCompartido, token=token, activo=True)

    # Si expira_en es None, no expira. Si existe, se valida.
    if doc.expira_en and timezone.now() > doc.expira_en:
        raise Http404("Documento no disponible.")

    if not doc.archivo:
        raise Http404("Documento no disponible.")

    # ✅ En Render + Cloudinary: lo más estable es redirigir al archivo
    return redirect(doc.archivo.url)
