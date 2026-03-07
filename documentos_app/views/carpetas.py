from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from documentos_app.forms import CarpetaForm
from documentos_app.models import Carpeta, Documento


@login_required
def carpeta_list(request):
    tenant = getattr(request, "tenant", None)

    carpetas = (
        Carpeta.objects.filter(tenant=tenant, activa=True)
        .select_related("carpeta_padre", "propietario")
        .order_by("nombre")
    )

    resumen_sidebar = {
        "total_carpetas": Carpeta.objects.filter(
            tenant=tenant,
            activa=True,
        ).count(),
        "total_documentos": Documento.objects.filter(
            tenant=tenant,
            eliminado=False,
        ).count(),
    }

    context = {
        "titulo_modulo": "Carpetas",
        "carpetas": carpetas,
        "resumen_sidebar": resumen_sidebar,
    }
    return render(request, "documentos_app/carpeta_list.html", context)


@login_required
def carpeta_create(request):
    tenant = getattr(request, "tenant", None)

    if request.method == "POST":
        form = CarpetaForm(request.POST, tenant=tenant)
        if form.is_valid():
            carpeta = form.save(commit=False)
            carpeta.tenant = tenant
            carpeta.propietario = request.user
            carpeta.activa = True
            carpeta.save()

            messages.success(request, "Carpeta creada correctamente.")
            return redirect("documentos_app:carpeta_list")
    else:
        form = CarpetaForm(tenant=tenant)

    resumen_sidebar = {
        "total_carpetas": Carpeta.objects.filter(
            tenant=tenant,
            activa=True,
        ).count(),
        "total_documentos": Documento.objects.filter(
            tenant=tenant,
            eliminado=False,
        ).count(),
    }

    context = {
        "titulo_modulo": "Nueva carpeta",
        "form": form,
        "resumen_sidebar": resumen_sidebar,
    }
    return render(request, "documentos_app/carpeta_form.html", context)