from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from documentos_app.models import Carpeta, CategoriaDocumento, Documento, EtiquetaDocumento


@login_required
def dashboard_documentos(request):
    tenant = getattr(request, "tenant", None)

    carpetas = Carpeta.objects.filter(tenant=tenant, activa=True).count()
    categorias = CategoriaDocumento.objects.filter(tenant=tenant, activa=True).count()
    etiquetas = EtiquetaDocumento.objects.filter(tenant=tenant, activa=True).count()
    documentos = Documento.objects.filter(tenant=tenant, eliminado=False).count()
    documentos_oficiales = Documento.objects.filter(
        tenant=tenant,
        eliminado=False,
        es_oficial=True,
    ).count()
    documentos_revision = Documento.objects.filter(
        tenant=tenant,
        eliminado=False,
        estado="revision",
    ).count()

    ultimos_documentos = Documento.objects.filter(
        tenant=tenant,
        eliminado=False,
    ).select_related("carpeta", "categoria").order_by("-created_at")[:10]

    context = {
        "titulo_modulo": "Gestión Documental",
        "carpetas_count": carpetas,
        "categorias_count": categorias,
        "etiquetas_count": etiquetas,
        "documentos_count": documentos,
        "documentos_oficiales_count": documentos_oficiales,
        "documentos_revision_count": documentos_revision,
        "ultimos_documentos": ultimos_documentos,
    }
    return render(request, "documentos_app/dashboard.html", context)