from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EvaluacionMiembroForm
from .models import EvaluacionMiembro

# Ajusta estos imports si tus modelos se llaman distinto
from estructura_app.models import Unidad
from miembros_app.models import Miembro


def get_unidades_del_lider(user):
    """
    Devuelve un queryset de Unidades donde este user es líder.
    AJUSTA AQUÍ según tu estructura real.

    Ejemplos típicos:
    - Si tienes Unidad.lider (FK) o Unidad.lideres (M2M)
    - Si tienes UnidadCargo con relación a User o Miembro
    """

    # ✅ Opción 1 (si tu Unidad tiene un campo lider (FK a User)):
    # return Unidad.objects.filter(lider=user).distinct()

    # ✅ Opción 2 (si Unidad tiene ManyToMany a User: lideres):
    # return Unidad.objects.filter(lideres=user).distinct()

    # ✅ Opción 3 (si usas UnidadCargo con miembro y tu User se vincula a Miembro):
    # from estructura_app.models import UnidadCargo
    # if not hasattr(user, 'miembro'):
    #     return Unidad.objects.none()
    # return Unidad.objects.filter(cargos__miembro=user.miembro, cargos__activo=True).distinct()

    # 🔴 Por defecto (para que no reviente): vacío hasta que lo conectes
    return Unidad.objects.none()


def validar_acceso_unidad(user, unidad: Unidad):
    unidades = get_unidades_del_lider(user)
    return unidades.filter(id=unidad.id).exists()


@login_required
def dashboard(request):
    return redirect('evaluaciones:mis_unidades')


@login_required
def mis_unidades(request):
    unidades = get_unidades_del_lider(request.user)
    return render(request, 'evaluaciones/mis_unidades.html', {'unidades': unidades})


@login_required
def unidad_miembros(request, unidad_id):
    unidad = get_object_or_404(Unidad, id=unidad_id)

    if not validar_acceso_unidad(request.user, unidad):
        raise Http404("No tienes acceso a esta unidad.")

    # Ajusta si tu relación de miembros por unidad es distinta
    miembros = Miembro.objects.filter(unidad=unidad).order_by('id')

    # Última evaluación por miembro (simple)
    ultimas = {}
    qs = (
        EvaluacionMiembro.objects
        .filter(unidad=unidad)
        .order_by('miembro_id', '-creado_en')
    )
    # Para no complicar con Subquery ahora, lo hacemos en memoria (suficiente para empezar)
    for ev in qs:
        if ev.miembro_id not in ultimas:
            ultimas[ev.miembro_id] = ev

    return render(request, 'evaluaciones/unidad_miembros.html', {
        'unidad': unidad,
        'miembros': miembros,
        'ultimas': ultimas,
    })


@login_required
def evaluar_miembro(request, unidad_id, miembro_id):
    unidad = get_object_or_404(Unidad, id=unidad_id)

    if not validar_acceso_unidad(request.user, unidad):
        raise Http404("No tienes acceso a esta unidad.")

    miembro = get_object_or_404(Miembro, id=miembro_id)

    # Protección extra: miembro debe pertenecer a la unidad
    # Ajusta si tu relación es distinta
    if getattr(miembro, 'unidad_id', None) != unidad.id:
        raise Http404("Este miembro no pertenece a esta unidad.")

    if request.method == 'POST':
        form = EvaluacionMiembroForm(request.POST)
        if form.is_valid():
            ev = form.save(commit=False)
            ev.unidad = unidad
            ev.miembro = miembro
            ev.evaluador = request.user
            ev.save()
            return redirect('evaluaciones:unidad_miembros', unidad_id=unidad.id)
    else:
        form = EvaluacionMiembroForm()

    return render(request, 'evaluaciones/evaluar_miembro.html', {
        'unidad': unidad,
        'miembro': miembro,
        'form': form,
    })
