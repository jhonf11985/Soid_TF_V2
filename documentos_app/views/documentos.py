from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from documentos_app.models import Carpeta, Documento


@login_required
def documento_list(request):
    tenant = getattr(request, "tenant", None)

    documentos = (
        Documento.objects.filter(tenant=tenant, eliminado=False)
        .select_related("carpeta", "categoria", "propietario", "creado_por")
        .order_by("-created_at")
    )

    carpetas = Carpeta.objects.filter(
        tenant=tenant,
        activa=True,
    ).order_by("nombre")

    q = (request.GET.get("q") or "").strip()
    carpeta_id = (request.GET.get("carpeta") or "").strip()

    if q:
        documentos = documentos.filter(titulo__icontains=q)

    if carpeta_id.isdigit():
        documentos = documentos.filter(carpeta_id=int(carpeta_id))

    resumen_sidebar = {
        "total_documentos": Documento.objects.filter(
            tenant=tenant,
            eliminado=False,
        ).count(),
        "total_carpetas": Carpeta.objects.filter(
            tenant=tenant,
            activa=True,
        ).count(),
    }

    context = {
        "titulo_modulo": "Documentos",
        "documentos": documentos,
        "carpetas": carpetas,
        "resumen_sidebar": resumen_sidebar,
        "filtros": {
            "q": q,
            "carpeta": carpeta_id,
        },
    }
    return render(request, "documentos_app/documento_list.html", context)