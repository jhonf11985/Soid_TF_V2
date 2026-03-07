from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from documentos_app.forms import CategoriaDocumentoForm
from documentos_app.models import Carpeta, CategoriaDocumento, Documento


@login_required
def categoria_list(request):
    tenant = getattr(request, "tenant", None)

    categorias = (
        CategoriaDocumento.objects.filter(tenant=tenant, activa=True)
        .order_by("nombre")
    )

    q = (request.GET.get("q") or "").strip()

    if q:
        categorias = categorias.filter(nombre__icontains=q)

    resumen_sidebar = {
        "total_categorias": CategoriaDocumento.objects.filter(
            tenant=tenant,
            activa=True,
        ).count(),
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
        "titulo_modulo": "Categorías",
        "categorias": categorias,
        "resumen_sidebar": resumen_sidebar,
        "filtros": {
            "q": q,
        },
    }
    return render(request, "documentos_app/categoria_list.html", context)


@login_required
def categoria_create(request):
    tenant = getattr(request, "tenant", None)

    if request.method == "POST":
        form = CategoriaDocumentoForm(request.POST, tenant=tenant)
        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.tenant = tenant

            if hasattr(categoria, "activa"):
                categoria.activa = True

            if hasattr(categoria, "creado_por"):
                categoria.creado_por = request.user

            if hasattr(categoria, "propietario"):
                categoria.propietario = request.user

            categoria.save()

            messages.success(request, "Categoría creada correctamente.")
            return redirect("documentos_app:categoria_list")
    else:
        form = CategoriaDocumentoForm(tenant=tenant)

    resumen_sidebar = {
        "total_categorias": CategoriaDocumento.objects.filter(
            tenant=tenant,
            activa=True,
        ).count(),
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
        "titulo_modulo": "Nueva categoría",
        "form": form,
        "resumen_sidebar": resumen_sidebar,
    }
    return render(request, "documentos_app/categoria_form.html", context)