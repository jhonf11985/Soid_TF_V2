from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from documentos_app.models import Documento


@login_required
def documento_list(request):
    tenant = getattr(request, "tenant", None)

    documentos = (
        Documento.objects.filter(tenant=tenant, eliminado=False)
        .select_related("carpeta", "categoria", "propietario", "creado_por")
        .prefetch_related("etiquetas")
        .order_by("-created_at")
    )

    context = {
        "titulo_modulo": "Documentos",
        "documentos": documentos,
    }
    return render(request, "documentos_app/documento_list.html", context)