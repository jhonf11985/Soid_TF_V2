# finanzas_app/views/categorias.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from ..models import CategoriaMovimiento
from ..forms import CategoriaMovimientoForm


@login_required
@require_GET
@permission_required("finanzas_app.view_categoriamovimiento", raise_exception=True)
def categorias_listado(request):
    """
    Listado de todas las categorías de movimiento.
    Permite filtrar por tipo (ingreso/egreso).
    """
    tenant = request.tenant  # 👈 TENANT
    
    categorias = CategoriaMovimiento.objects.filter(
        tenant=tenant  # 👈 FILTRAR POR TENANT
    ).order_by("tipo", "nombre")

    # Filtro por tipo
    filtro_tipo = request.GET.get("tipo")
    if filtro_tipo in ["ingreso", "egreso"]:
        categorias = categorias.filter(tipo=filtro_tipo)

    # Contadores
    base_qs = CategoriaMovimiento.objects.filter(tenant=tenant)  # 👈 FILTRAR POR TENANT
    total_todas = base_qs.count()
    total_ingresos = base_qs.filter(tipo="ingreso").count()
    total_egresos = base_qs.filter(tipo="egreso").count()

    context = {
        "categorias": categorias,
        "filtro_tipo": filtro_tipo,
        "total_todas": total_todas,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
    }
    return render(request, "finanzas_app/categorias_listado.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.add_categoriamovimiento", raise_exception=True)
def categoria_crear(request):
    """
    Crear una nueva categoría de movimiento.
    """
    tenant = request.tenant  # 👈 TENANT
    
    if request.method == "POST":
        form = CategoriaMovimientoForm(request.POST, tenant=tenant)  # 👈 PASAR TENANT
        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.tenant = tenant  # 👈 ASIGNAR TENANT
            categoria.save()
            messages.success(request, f"Categoría «{categoria.nombre}» creada correctamente.")
            return redirect("finanzas_app:categorias_listado")
    else:
        # Pre-seleccionar tipo si viene en la URL
        tipo_inicial = request.GET.get("tipo", "ingreso")
        form = CategoriaMovimientoForm(initial={"tipo": tipo_inicial}, tenant=tenant)  # 👈 PASAR TENANT

    context = {
        "form": form,
        "categoria": None,
    }
    return render(request, "finanzas_app/categoria_form.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@permission_required("finanzas_app.change_categoriamovimiento", raise_exception=True)
def categoria_editar(request, pk):
    """
    Editar una categoría de movimiento existente.
    """
    tenant = request.tenant  # 👈 TENANT
    categoria = get_object_or_404(CategoriaMovimiento, pk=pk, tenant=tenant)  # 👈 FILTRAR POR TENANT

    if request.method == "POST":
        form = CategoriaMovimientoForm(request.POST, instance=categoria, tenant=tenant)  # 👈 PASAR TENANT
        if form.is_valid():
            form.save()
            messages.success(request, f"Categoría «{categoria.nombre}» actualizada correctamente.")
            return redirect("finanzas_app:categorias_listado")
    else:
        form = CategoriaMovimientoForm(instance=categoria, tenant=tenant)  # 👈 PASAR TENANT

    context = {
        "form": form,
        "categoria": categoria,
    }
    return render(request, "finanzas_app/categoria_form.html", context)


@login_required
@require_POST
@permission_required("finanzas_app.change_categoriamovimiento", raise_exception=True)
def categoria_toggle(request, pk):
    """
    Activar o desactivar una categoría.
    No eliminamos para mantener el historial de movimientos.
    """
    tenant = request.tenant  # 👈 TENANT
    categoria = get_object_or_404(CategoriaMovimiento, pk=pk, tenant=tenant)  # 👈 FILTRAR POR TENANT

    # Toggle del estado
    categoria.activo = not categoria.activo
    categoria.save()

    if categoria.activo:
        messages.success(request, f"Categoría «{categoria.nombre}» activada.")
    else:
        messages.warning(request, f"Categoría «{categoria.nombre}» desactivada.")

    return redirect("finanzas_app:categorias_listado")


def categoria_sugerir_codigo(request):
    """
    API para sugerir código de categoría basado en el nombre.
    """
    from django.http import JsonResponse
    
    nombre = request.GET.get("nombre", "").strip()
    tipo = request.GET.get("tipo", "ingreso").strip()
    
    if not nombre:
        return JsonResponse({"codigo": ""})
    
    # Generar código sugerido
    prefijo = "ING" if tipo == "ingreso" else "EGR"
    
    # Limpiar nombre: quitar acentos, espacios, caracteres especiales
    import unicodedata
    nombre_limpio = unicodedata.normalize('NFKD', nombre)
    nombre_limpio = nombre_limpio.encode('ASCII', 'ignore').decode('ASCII')
    nombre_limpio = nombre_limpio.upper().replace(" ", "_")
    
    # Quitar caracteres no alfanuméricos excepto _
    import re
    nombre_limpio = re.sub(r'[^A-Z0-9_]', '', nombre_limpio)
    
    codigo_sugerido = f"{prefijo}_{nombre_limpio}"
    
    # Limitar longitud
    if len(codigo_sugerido) > 50:
        codigo_sugerido = codigo_sugerido[:50]
    
    return JsonResponse({"codigo": codigo_sugerido})