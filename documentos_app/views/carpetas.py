from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from documentos_app.models import Carpeta


@login_required
def carpeta_list(request):
    tenant = getattr(request, "tenant", None)

    carpetas = (
        Carpeta.objects.filter(tenant=tenant, activa=True)
        .select_related("carpeta_padre", "propietario")
        .order_by("orden", "nombre")
    )

    context = {
        "titulo_modulo": "Carpetas",
        "carpetas": carpetas,
    }
    return render(request, "documentos_app/carpeta_list.html", context)