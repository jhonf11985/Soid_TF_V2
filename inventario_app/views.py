
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render

from .forms import RecursoForm
from .models import MovimientoRecurso, Recurso


def _resumen_sidebar():
    return Recurso.objects.aggregate(
        total=Count("id"),
        disponibles=Count("id", filter=Q(estado=Recurso.Estados.DISPONIBLE)),
        en_uso=Count("id", filter=Q(estado=Recurso.Estados.EN_USO)),
        en_reparacion=Count("id", filter=Q(estado=Recurso.Estados.EN_REPARACION)),
    )


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


# ─────────────────────────────────────────────
# RECURSOS
# ─────────────────────────────────────────────

@login_required
def recursos_lista(request):
    # Placeholder por ahora (luego hacemos listado real con filtros)
    return render(request, "inventario_app/placeholder.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "titulo": "Recursos",
        "mensaje": "Listado en construcción. Próximo: tabla + filtros + búsqueda.",
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
    })


# ─────────────────────────────────────────────
# MOVIMIENTOS / CONFIG (placeholders por ahora)
# ─────────────────────────────────────────────

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
def categorias_lista(request):
    return render(request, "inventario_app/placeholder.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "titulo": "Categorías",
        "mensaje": "CRUD en construcción.",
    })


@login_required
def ubicaciones_lista(request):
    return render(request, "inventario_app/placeholder.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "titulo": "Ubicaciones",
        "mensaje": "CRUD en construcción.",
    })


@login_required
def reportes(request):
    return render(request, "inventario_app/placeholder.html", {
        "resumen_sidebar": _resumen_sidebar(),
        "titulo": "Reportes",
        "mensaje": "Reportes en construcción.",
    })

