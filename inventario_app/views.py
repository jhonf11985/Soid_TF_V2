from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render

from .forms import RecursoForm, CategoriaRecursoForm, UbicacionForm
from .models import MovimientoRecurso, Recurso, CategoriaRecurso, Ubicacion


def _resumen_sidebar():
    return Recurso.objects.aggregate(
        total=Count("id"),
        disponibles=Count("id", filter=Q(estado=Recurso.Estados.DISPONIBLE)),
        en_uso=Count("id", filter=Q(estado=Recurso.Estados.EN_USO)),
        en_reparacion=Count("id", filter=Q(estado=Recurso.Estados.EN_REPARACION)),
    )


# ─────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────

@login_required
def dashboard(request):
    stats = Recurso.objects.aggregate(
        total=Count("id"),
        disponibles=Count("id", filter=Q(estado=Recurso.Estados.DISPONIBLE)),
        en_uso=Count("id", filter=Q(estado=Recurso.Estados.EN_USO)),
        prestados=Count("id", filter=Q(estado=Recurso.Estados.PRESTADO)),
        en_reparacion=Count("id", filter=Q(estado=Recurso.Estados.EN_REPARACION)),
        danados=Count("id", filter=Q(estado=Recurso.Estados.DANADO)),
        baja=Count("id", filter=Q(estado=Recurso.Estados.BAJA)),
    )

    ultimos_movimientos = (
        MovimientoRecurso.objects
        .select_related("recurso", "ubicacion_origen", "ubicacion_destino")
        .order_by("-fecha")[:12]
    )

    return render(request, "inventario_app/dashboard.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "stats": stats,
        "ultimos_movimientos": ultimos_movimientos,
    })


# ─────────────────────────────────────────────────────
# RECURSOS
# ─────────────────────────────────────────────────────

@login_required
def recursos_lista(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    categoria = (request.GET.get("categoria") or "").strip()
    ubicacion_filter = (request.GET.get("ubicacion") or "").strip()

    recursos = (
        Recurso.objects
        .select_related("categoria", "ubicacion")
        .order_by("nombre", "codigo")
    )

    if q:
        recursos = recursos.filter(
            Q(codigo__icontains=q) | Q(nombre__icontains=q)
        )

    if estado:
        recursos = recursos.filter(estado=estado)

    if categoria:
        recursos = recursos.filter(categoria_id=categoria)

    if ubicacion_filter:
        recursos = recursos.filter(ubicacion_id=ubicacion_filter)

    # Contadores para resumen
    total_disponibles = Recurso.objects.filter(estado=Recurso.Estados.DISPONIBLE).count()
    total_en_uso = Recurso.objects.filter(estado=Recurso.Estados.EN_USO).count()
    total_prestados = Recurso.objects.filter(estado=Recurso.Estados.PRESTADO).count()
    total_reparacion = Recurso.objects.filter(estado=Recurso.Estados.EN_REPARACION).count()

    # Opciones para filtros
    categorias = CategoriaRecurso.objects.filter(activo=True).order_by("nombre")
    ubicaciones = Ubicacion.objects.order_by("nombre")

    return render(request, "inventario_app/recursos_lista.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "recursos": recursos,
        "q": q,
        "estado": estado,
        "categoria": categoria,
        "ubicacion": ubicacion_filter,
        "ESTADOS": Recurso.Estados.choices,
        "categorias": categorias,
        "ubicaciones": ubicaciones,
        "total_disponibles": total_disponibles,
        "total_en_uso": total_en_uso,
        "total_prestados": total_prestados,
        "total_reparacion": total_reparacion,
        "titulo": "Recursos",
    })


@login_required
def recurso_nuevo(request):
    if request.method == "POST":
        form = RecursoForm(request.POST, request.FILES)
        if form.is_valid():
            recurso = form.save()
            messages.success(request, f"Recurso creado: {recurso.codigo} - {recurso.nombre}")
            return redirect("inventario:recursos_lista")
        messages.error(request, "Revisa los campos marcados.")
    else:
        form = RecursoForm()

    return render(request, "inventario_app/recurso_form.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "form": form,
        "titulo": "Nuevo recurso",
    })


@login_required
def recurso_detalle(request, pk):
    recurso = Recurso.objects.select_related("categoria", "ubicacion").get(pk=pk)
    movimientos = recurso.movimientos.select_related(
        "ubicacion_origen", "ubicacion_destino"
    ).order_by("-fecha")[:10]

    return render(request, "inventario_app/recurso_detalle.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "recurso": recurso,
        "movimientos": movimientos,
        "titulo": f"{recurso.codigo} - {recurso.nombre}",
    })


@login_required
def recurso_editar(request, pk):
    recurso = Recurso.objects.get(pk=pk)

    if request.method == "POST":
        form = RecursoForm(request.POST, request.FILES, instance=recurso)
        if form.is_valid():
            form.save()
            messages.success(request, f"Recurso actualizado: {recurso.codigo}")
            return redirect("inventario:recurso_detalle", pk=recurso.pk)
        messages.error(request, "Revisa los campos marcados.")
    else:
        form = RecursoForm(instance=recurso)

    return render(request, "inventario_app/recurso_form.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "form": form,
        "obj": recurso,
        "modo": "editar",
        "titulo": f"Editar: {recurso.codigo}",
    })


# ─────────────────────────────────────────────────────
# CATEGORÍAS
# ─────────────────────────────────────────────────────

@login_required
def categorias_lista(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()

    categorias = (
        CategoriaRecurso.objects
        .annotate(total_recursos=Count("recursos"))
        .order_by("nombre")
    )

    if q:
        categorias = categorias.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q)
        )

    if estado == "activo":
        categorias = categorias.filter(activo=True)
    elif estado == "inactivo":
        categorias = categorias.filter(activo=False)

    # Contadores para resumen
    total_activas = CategoriaRecurso.objects.filter(activo=True).count()
    total_inactivas = CategoriaRecurso.objects.filter(activo=False).count()

    return render(request, "inventario_app/categorias_lista.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "categorias": categorias,
        "q": q,
        "estado": estado,
        "total_activas": total_activas,
        "total_inactivas": total_inactivas,
        "titulo": "Categorías",
    })


@login_required
def categoria_nueva(request):
    if request.method == "POST":
        form = CategoriaRecursoForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            messages.success(
                request,
                f"Categoría creada correctamente: {categoria.nombre}"
            )
            return redirect("inventario:categorias_lista")
        messages.error(request, "Revisa los campos marcados.")
    else:
        form = CategoriaRecursoForm()

    return render(request, "inventario_app/categoria_form.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "form": form,
        "titulo": "Nueva categoría",
    })


# ─────────────────────────────────────────────────────
# UBICACIONES
# ─────────────────────────────────────────────────────

@login_required
def ubicaciones_lista(request):
    q = (request.GET.get("q") or "").strip()

    ubicaciones = (
        Ubicacion.objects
        .annotate(total_recursos=Count("recursos"))
        .order_by("nombre")
    )

    if q:
        ubicaciones = ubicaciones.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q)
        )

    return render(request, "inventario_app/ubicaciones_lista.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "ubicaciones": ubicaciones,
        "q": q,
        "titulo": "Ubicaciones",
    })


@login_required
def ubicacion_nueva(request):
    if request.method == "POST":
        form = UbicacionForm(request.POST)
        if form.is_valid():
            ubicacion = form.save()
            messages.success(
                request,
                f"Ubicación creada correctamente: {ubicacion.nombre}"
            )
            return redirect("inventario:ubicaciones_lista")
        messages.error(request, "Revisa los campos marcados.")
    else:
        form = UbicacionForm()

    return render(request, "inventario_app/ubicacion_form.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "form": form,
        "titulo": "Nueva ubicación",
    })


@login_required
def ubicacion_editar(request, pk):
    ubicacion = Ubicacion.objects.get(pk=pk)
    
    if request.method == "POST":
        form = UbicacionForm(request.POST, instance=ubicacion)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ubicación actualizada: {ubicacion.nombre}")
            return redirect("inventario:ubicaciones_lista")
        messages.error(request, "Revisa los campos marcados.")
    else:
        form = UbicacionForm(instance=ubicacion)

    return render(request, "inventario_app/ubicacion_form.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "form": form,
        "obj": ubicacion,
        "modo": "editar",
        "titulo": f"Editar: {ubicacion.nombre}",
    })


# ─────────────────────────────────────────────────────
# MOVIMIENTOS / REPORTES (placeholders)
# ─────────────────────────────────────────────────────

@login_required
def movimientos_lista(request):
    return render(request, "inventario_app/placeholder.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "titulo": "Movimientos",
        "mensaje": "Historial en construcción.",
    })


@login_required
def movimiento_nuevo(request):
    return render(request, "inventario_app/placeholder.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "titulo": "Registrar movimiento",
        "mensaje": "Wizard en construcción.",
    })


@login_required
def reportes(request):
    return render(request, "inventario_app/placeholder.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "titulo": "Reportes",
        "mensaje": "Reportes en construcción.",
    })