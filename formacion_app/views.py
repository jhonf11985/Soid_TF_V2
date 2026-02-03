from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count

from .models import ProgramaEducativo, CicloPrograma, GrupoFormativo, InscripcionGrupo
from .forms import ProgramaEducativoForm


# =============================================================================
# DASHBOARD
# =============================================================================

def inicio_formacion(request):
    """Dashboard principal del módulo de formación."""
    total_programas = ProgramaEducativo.objects.count()
    programas_activos = ProgramaEducativo.objects.filter(activo=True).count()
    programas_inactivos = ProgramaEducativo.objects.filter(activo=False).count()

    total_ciclos = CicloPrograma.objects.count()
    ciclos_activos = CicloPrograma.objects.filter(activo=True).count()

    total_grupos = GrupoFormativo.objects.count()
    grupos_sin_maestro = GrupoFormativo.objects.filter(maestro__isnull=True).count()
    grupos_sin_maestro_lista = (
        GrupoFormativo.objects
        .filter(maestro__isnull=True)
        .select_related("programa")[:10]
    )


    total_inscritos = InscripcionGrupo.objects.count()
    inscritos_activos = InscripcionGrupo.objects.filter(estado="ACTIVO").count()

    # Donut: distribución por sexo permitido
    distribucion = (
        GrupoFormativo.objects
        .values("sexo_permitido")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    mapa = {"VARONES": "Varones", "HEMBRAS": "Hembras", "MIXTO": "Mixto"}
    distribucion_sexo = [
        {"label": mapa.get(r["sexo_permitido"], r["sexo_permitido"]), "total": r["total"]}
        for r in distribucion
    ]

    # Top programas por inscritos (vía grupos → inscripciones)
    top_programas = (
        ProgramaEducativo.objects
        .annotate(total_inscritos=Count("grupos__inscripciones"))
        .order_by("-total_inscritos", "nombre")[:5]
    )


    ctx = {
        "total_programas": total_programas,
        "programas_activos": programas_activos,
        "programas_inactivos": programas_inactivos,
        "total_ciclos": total_ciclos,
        "ciclos_activos": ciclos_activos,
        "total_grupos": total_grupos,
        "grupos_sin_maestro": grupos_sin_maestro,
        "grupos_sin_maestro_lista": grupos_sin_maestro_lista,
        "total_inscritos": total_inscritos,
        "inscritos_activos": inscritos_activos,
        "distribucion_sexo": distribucion_sexo,
        "top_programas": top_programas,
    }
    return render(request, "formacion_app/dashboard.html", ctx)


# =============================================================================
# PROGRAMAS EDUCATIVOS
# =============================================================================

def programas_list(request):
    """Listado de todos los programas educativos."""
    programas = ProgramaEducativo.objects.all()
    return render(request, "formacion_app/programas_list.html", {
        "programas": programas
    })


def programa_crear(request):
    """Crear un nuevo programa educativo."""
    if request.method == "POST":
        form = ProgramaEducativoForm(request.POST)
        if form.is_valid():
            programa = form.save()

            if "guardar_y_nuevo" in request.POST:
                return redirect("formacion:programa_crear")

            return redirect("formacion:programa_editar", pk=programa.pk)
    else:
        form = ProgramaEducativoForm()

    return render(request, "formacion_app/programa_form.html", {
        "form": form,
        "programa": None,
    })


def programa_editar(request, pk):
    """Editar un programa educativo existente."""
    programa = get_object_or_404(ProgramaEducativo, pk=pk)

    if request.method == "POST":
        form = ProgramaEducativoForm(request.POST, instance=programa)
        if form.is_valid():
            form.save()

            if "guardar_y_nuevo" in request.POST:
                return redirect("formacion:programa_crear")

            return redirect("formacion:programa_editar", pk=programa.pk)
    else:
        form = ProgramaEducativoForm(instance=programa)

    return render(request, "formacion_app/programa_form.html", {
        "form": form,
        "programa": programa,
    })

# =============================================================================
# GRUPOS / CLASES
# =============================================================================

def grupos_listado(request):
    """
    Listado de grupos formativos.
    """
    grupos = (
        GrupoFormativo.objects
        .select_related("programa", "maestro")
        .order_by("nombre")
    )

    return render(request, "formacion_app/grupos_list.html", {
        "grupos": grupos,
    })


def grupo_crear(request):
    """
    Crear un nuevo grupo/clase.
    """
    if request.method == "POST":
        grupo = GrupoFormativo(
            nombre=request.POST.get("nombre"),
            programa_id=request.POST.get("programa") or None,
            sexo_permitido=request.POST.get("sexo_permitido", "MIXTO"),
            edad_min=request.POST.get("edad_min") or None,
            edad_max=request.POST.get("edad_max") or None,
            maestro_id=request.POST.get("maestro") or None,
            horario=request.POST.get("horario", ""),
            lugar=request.POST.get("lugar", ""),
            cupo=request.POST.get("cupo") or None,
            activo=("activo" in request.POST),
        )
        grupo.full_clean()
        grupo.save()
        return redirect("formacion:grupo_editar", pk=grupo.pk)

    programas = ProgramaEducativo.objects.filter(activo=True).order_by("nombre")

    return render(request, "formacion_app/grupo_form.html", {
        "grupo": None,
        "programas": programas,
    })


def grupo_editar(request, pk):
    """
    Editar un grupo/clase existente.
    """
    grupo = get_object_or_404(GrupoFormativo, pk=pk)

    if request.method == "POST":
        grupo.nombre = request.POST.get("nombre")
        grupo.programa_id = request.POST.get("programa") or None
        grupo.sexo_permitido = request.POST.get("sexo_permitido", "MIXTO")
        grupo.edad_min = request.POST.get("edad_min") or None
        grupo.edad_max = request.POST.get("edad_max") or None
        grupo.maestro_id = request.POST.get("maestro") or None
        grupo.horario = request.POST.get("horario", "")
        grupo.lugar = request.POST.get("lugar", "")
        grupo.cupo = request.POST.get("cupo") or None
        grupo.activo = "activo" in request.POST

        grupo.full_clean()
        grupo.save()

        return redirect("formacion:grupo_editar", pk=grupo.pk)

    programas = ProgramaEducativo.objects.filter(activo=True).order_by("nombre")

    return render(request, "formacion_app/grupo_form.html", {
        "grupo": grupo,
        "programas": programas,
    })

def ciclo_crear(request):
    """Crear un nuevo ciclo de programa."""
    if request.method == "POST":
        form = CicloProgramaForm(request.POST)
        if form.is_valid():
            ciclo = form.save()

            if "guardar_y_nuevo" in request.POST:
                return redirect("formacion:ciclo_crear")

            return redirect("formacion:ciclo_editar", pk=ciclo.pk)
    else:
        form = CicloProgramaForm()

    return render(request, "formacion_app/ciclo_form.html", {
        "form": form,
        "ciclo": None,
    })

def ciclo_editar(request, pk):
    """Editar un ciclo existente."""
    ciclo = get_object_or_404(CicloPrograma, pk=pk)

    if request.method == "POST":
        form = CicloProgramaForm(request.POST, instance=ciclo)
        if form.is_valid():
            form.save()

            if "guardar_y_nuevo" in request.POST:
                return redirect("formacion:ciclo_crear")

            return redirect("formacion:ciclo_editar", pk=ciclo.pk)
    else:
        form = CicloProgramaForm(instance=ciclo)

    return render(request, "formacion_app/ciclo_form.html", {
        "form": form,
        "ciclo": ciclo,
    })
