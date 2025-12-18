from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UnidadForm
from .models import Unidad

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from .models import Unidad, TipoUnidad, RolUnidad, UnidadMembresia, UnidadCargo

@login_required
def estructura_home(request):
    return render(request, "estructura_app/home.html")



@login_required
def dashboard(request):
    # KPIs
    total_unidades = Unidad.objects.count()
    total_tipos = TipoUnidad.objects.filter(activo=True).count()
    total_roles = RolUnidad.objects.filter(activo=True).count()

    # Líderes vigentes (solo cargos marcados como liderazgo)
    lideres_vigentes = UnidadCargo.objects.filter(
        vigente=True,
        rol__es_liderazgo=True
    ).count()

    # Unidades activas / inactivas
    unidades_activas = Unidad.objects.filter(activa=True).count()
    unidades_inactivas = Unidad.objects.filter(activa=False).count()

    # Unidades sin líder vigente (con rol liderazgo)
    unidades_con_lider = UnidadCargo.objects.filter(
        vigente=True,
        rol__es_liderazgo=True
    ).values_list("unidad_id", flat=True).distinct()

    unidades_sin_lider = Unidad.objects.filter(activa=True).exclude(id__in=unidades_con_lider).count()

    # Top unidades por miembros (solo activos)
    top_unidades = (
        Unidad.objects.annotate(
            total_miembros=Count("membresias", filter=Q(membresias__activo=True))
        )
        .order_by("-total_miembros", "nombre")[:6]
    )

    # Distribución por tipo
    distribucion_por_tipo = (
        TipoUnidad.objects.filter(activo=True)
        .annotate(total=Count("unidades"))
        .order_by("orden", "nombre")
    )

    context = {
        "total_unidades": total_unidades,
        "total_tipos": total_tipos,
        "total_roles": total_roles,
        "lideres_vigentes": lideres_vigentes,
        "unidades_activas": unidades_activas,
        "unidades_inactivas": unidades_inactivas,
        "unidades_sin_lider": unidades_sin_lider,
        "top_unidades": top_unidades,
        "distribucion_por_tipo": distribucion_por_tipo,
    }
    return render(request, "estructura_app/dashboard.html", context)


@login_required
def unidad_crear(request):
    if request.method == "POST":
        form = UnidadForm(request.POST)
        if form.is_valid():
            unidad = form.save()

            messages.success(request, "Unidad creada correctamente.")

            # Botón “Guardar y nuevo”
            if request.POST.get("guardar_y_nuevo") == "1":
                return redirect("estructura_app:unidad_crear")

            # Si solo guardas, te mando a editar (patrón Odoo)
            return redirect("estructura_app:unidad_editar", pk=unidad.pk)
        else:
            messages.error(request, "Revisa los campos marcados. Hay errores en el formulario.")
    else:
        form = UnidadForm()

    context = {
        "form": form,
        "modo": "crear",
        "unidad": None,
    }
    return render(request, "estructura_app/unidad_form.html", context)


@login_required
def unidad_editar(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)

    if request.method == "POST":
        form = UnidadForm(request.POST, instance=unidad)
        if form.is_valid():
            form.save()
            messages.success(request, "Cambios guardados correctamente.")
            return redirect("estructura_app:unidad_editar", pk=unidad.pk)
        else:
            messages.error(request, "Revisa los campos marcados. Hay errores en el formulario.")
    else:
        form = UnidadForm(instance=unidad)

    context = {
        "form": form,
        "modo": "editar",
        "unidad": unidad,
    }
    return render(request, "estructura_app/unidad_form.html", context)



def unidad_listado(request):
    query = request.GET.get('q', '').strip()

    unidades = Unidad.objects.all().order_by('nombre')
    if query:
        unidades = unidades.filter(nombre__icontains=query) | unidades.filter(codigo__icontains=query)

    return render(request, 'estructura_app/unidad_listado.html', {
        'unidades': unidades,
        'query': query,
    })

def unidad_detalle(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)
    return render(request, 'estructura_app/unidad_detalle.html', {'unidad': unidad})

