# finanzas_app/views/proveedores.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET, require_http_methods
from django.db.models import Q

from ..models import ProveedorFinanciero
from ..forms import ProveedorFinancieroForm


@login_required
@require_GET
@permission_required("finanzas_app.view_proveedorfinanciero", raise_exception=True)
def proveedores_list(request):
    """
    Listado de proveedores financieros.
    """
    tenant = request.tenant  # 👈 TENANT
    q = (request.GET.get("q") or "").strip()

    qs = ProveedorFinanciero.objects.filter(tenant=tenant)  # 👈 FILTRAR POR TENANT
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(telefono__icontains=q) |
            Q(email__icontains=q)
        )
    qs = qs.order_by("nombre")

    return render(request, "finanzas_app/cxp/proveedores_lista.html", {"items": qs, "q": q})


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.add_proveedorfinanciero", raise_exception=True)
def proveedores_create(request):
    """
    Crear un nuevo proveedor financiero.
    """
    tenant = request.tenant  # 👈 TENANT
    
    if request.method == "POST":
        form = ProveedorFinancieroForm(request.POST, tenant=tenant)  # 👈 PASAR TENANT
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant = tenant  # 👈 ASIGNAR TENANT
            obj.save()
            messages.success(request, "✅ Proveedor creado correctamente.")
            return redirect("finanzas_app:proveedores_list")
    else:
        form = ProveedorFinancieroForm(tenant=tenant)  # 👈 PASAR TENANT

    return render(request, "finanzas_app/cxp/proveedores_crear.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.change_proveedorfinanciero", raise_exception=True)
def proveedores_editar(request, pk):
    """
    Editar un proveedor financiero existente.
    """
    tenant = request.tenant  # 👈 TENANT
    proveedor = get_object_or_404(ProveedorFinanciero, pk=pk, tenant=tenant)  # 👈 FILTRAR POR TENANT

    if request.method == "POST":
        form = ProveedorFinancieroForm(request.POST, instance=proveedor, tenant=tenant)  # 👈 PASAR TENANT
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Proveedor actualizado correctamente.")
            return redirect("finanzas_app:proveedores_list")
    else:
        form = ProveedorFinancieroForm(instance=proveedor, tenant=tenant)  # 👈 PASAR TENANT

    return render(
        request,
        "finanzas_app/cxp/proveedores_crear.html",
        {
            "form": form,
            "proveedor": proveedor,
            "modo": "editar",
        },
    )