from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count
from django.contrib import messages

from .models import ProgramaEducativo, CicloPrograma, GrupoFormativo, InscripcionGrupo
from .forms import ProgramaEducativoForm, CicloProgramaForm
from miembros_app.models import Miembro
from .utils_reglas import reporte_reglas_grupo


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
    grupos_sin_maestro = GrupoFormativo.objects.filter(maestros__isnull=True).count()
    grupos_sin_maestro_lista = (
        GrupoFormativo.objects
        .filter(maestros__isnull=True)
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

    # Top programas por inscritos
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
    """Listado de grupos formativos."""
    grupos = (
        GrupoFormativo.objects
        .select_related("programa")
        .prefetch_related("maestros", "ayudantes")
        .annotate(total_alumnos=Count("inscripciones", distinct=True))
        .order_by("nombre")
    )
    return render(request, "formacion_app/grupos_list.html", {
        "grupos": grupos,
    })


def _parse_ids(ids_string):
    """Convierte string de IDs separados por coma a lista de enteros."""
    if not ids_string:
        return []
    return [int(id.strip()) for id in ids_string.split(',') if id.strip().isdigit()]


def _get_miembros_data(miembros_queryset):
    """Convierte queryset de miembros a lista de diccionarios para el template."""
    return [
        {
            'id': m.id,
            'nombre': f"{m.nombres} {m.apellidos}".strip(),
            'codigo': m.codigo_miembro or ''
        }
        for m in miembros_queryset
    ]


def grupo_crear(request):
    """Crear un nuevo grupo/clase."""
    if request.method == "POST":
        try:
            # Crear grupo
            grupo = GrupoFormativo(
                nombre=request.POST.get("nombre"),
                programa_id=request.POST.get("programa") or None,
                sexo_permitido=request.POST.get("sexo_permitido", "MIXTO"),
                estado_civil_permitido=request.POST.get("estado_civil_permitido", "TODOS"),
                edad_min=request.POST.get("edad_min") or None,
                edad_max=request.POST.get("edad_max") or None,
                horario=request.POST.get("horario", ""),
                lugar=request.POST.get("lugar", ""),
                cupo=request.POST.get("cupo") or None,
                activo=("activo" in request.POST),
            )
            grupo.full_clean()
            grupo.save()

            # Asignar maestros
            maestros_ids = _parse_ids(request.POST.get("maestros_ids", ""))
            if maestros_ids:
                maestros = Miembro.objects.filter(id__in=maestros_ids)
                grupo.maestros.set(maestros)

            # Asignar ayudantes
            ayudantes_ids = _parse_ids(request.POST.get("ayudantes_ids", ""))
            if ayudantes_ids:
                ayudantes = Miembro.objects.filter(id__in=ayudantes_ids)
                grupo.ayudantes.set(ayudantes)

            # Inscribir estudiantes
            estudiantes_ids = _parse_ids(request.POST.get("estudiantes_ids", ""))
            for miembro_id in estudiantes_ids:
                InscripcionGrupo.objects.get_or_create(
                    miembro_id=miembro_id,
                    grupo=grupo,
                    defaults={'estado': 'ACTIVO'}
                )

            messages.success(request, f"Grupo '{grupo.nombre}' creado exitosamente.")
            return redirect("formacion:grupo_editar", pk=grupo.pk)

        except Exception as e:
            return render(request, "formacion_app/grupo_form.html", {
                "grupo": None,
                "programas": ProgramaEducativo.objects.filter(activo=True).order_by("nombre"),
                "errors": str(e),
            })

    programas = ProgramaEducativo.objects.filter(activo=True).order_by("nombre")

    return render(request, "formacion_app/grupo_form.html", {
        "grupo": None,
        "programas": programas,
    })


def grupo_editar(request, pk):
    """Editar un grupo/clase existente."""
    grupo = get_object_or_404(GrupoFormativo, pk=pk)

    if request.method == "POST":
        try:
            # Actualizar campos básicos
            grupo.nombre = request.POST.get("nombre")
            grupo.programa_id = request.POST.get("programa") or None
            grupo.sexo_permitido = request.POST.get("sexo_permitido", "MIXTO")
            grupo.estado_civil_permitido = request.POST.get("estado_civil_permitido", "TODOS")
            grupo.edad_min = request.POST.get("edad_min") or None
            grupo.edad_max = request.POST.get("edad_max") or None
            grupo.horario = request.POST.get("horario", "")
            grupo.lugar = request.POST.get("lugar", "")
            grupo.cupo = request.POST.get("cupo") or None
            grupo.activo = "activo" in request.POST

            grupo.full_clean()
            grupo.save()

            # Actualizar maestros
            maestros_ids = _parse_ids(request.POST.get("maestros_ids", ""))
            grupo.maestros.set(Miembro.objects.filter(id__in=maestros_ids))

            # Actualizar ayudantes
            ayudantes_ids = _parse_ids(request.POST.get("ayudantes_ids", ""))
            grupo.ayudantes.set(Miembro.objects.filter(id__in=ayudantes_ids))

            # Actualizar estudiantes (inscripciones)
            estudiantes_ids_nuevos = set(_parse_ids(request.POST.get("estudiantes_ids", "")))
            estudiantes_ids_actuales = set(
                grupo.inscripciones.filter(estado="ACTIVO").values_list('miembro_id', flat=True)
            )

            # Agregar nuevos
            for miembro_id in estudiantes_ids_nuevos - estudiantes_ids_actuales:
                InscripcionGrupo.objects.get_or_create(
                    miembro_id=miembro_id,
                    grupo=grupo,
                    defaults={'estado': 'ACTIVO'}
                )

            # Retirar los que ya no están
            for miembro_id in estudiantes_ids_actuales - estudiantes_ids_nuevos:
                InscripcionGrupo.objects.filter(
                    miembro_id=miembro_id,
                    grupo=grupo
                ).update(estado='RETIRADO')

            messages.success(request, "Grupo actualizado exitosamente.")
            return redirect("formacion:grupo_editar", pk=grupo.pk)

        except Exception as e:
            # Si hay error, recargar con datos actuales
            pass

    # Preparar datos para el template
    programas = ProgramaEducativo.objects.filter(activo=True).order_by("nombre")

    # Obtener maestros actuales
    maestros_actuales = _get_miembros_data(grupo.maestros.all())

    # Obtener ayudantes actuales
    ayudantes_actuales = _get_miembros_data(grupo.ayudantes.all())

    # Obtener estudiantes activos
    estudiantes_qs = Miembro.objects.filter(
        inscripciones_formacion__grupo=grupo,
        inscripciones_formacion__estado="ACTIVO"
    )
    estudiantes_actuales = _get_miembros_data(estudiantes_qs)

    # Contar equipo y alumnos para badges en pestañas
    total_equipo = len(maestros_actuales) + len(ayudantes_actuales)
    total_alumnos = len(estudiantes_actuales)

    # --- SUGERIDOS POR REGLAS (NO BLOQUEA, SOLO SUGIERE) ---
    reporte = reporte_reglas_grupo(grupo)

    # Para no cargar demasiado la UI
    sugeridos_faltan = _get_miembros_data(reporte["faltan"][:50])
    sugeridos_sobran = _get_miembros_data(reporte["sobran"][:50])
    sugeridos_elegibles = _get_miembros_data(reporte["elegibles"][:50])

    sugeridos_stats = {
        "total_elegibles": reporte["elegibles"].count(),
        "total_inscritos": reporte["inscritos"].count(),
        "total_faltan": reporte["faltan"].count(),
        "total_sobran": reporte["sobran"].count(),
    }

    return render(request, "formacion_app/grupo_form.html", {
        "grupo": grupo,
        "programas": programas,
        "maestros_actuales": maestros_actuales,
        "ayudantes_actuales": ayudantes_actuales,
        "estudiantes_actuales": estudiantes_actuales,
        "total_equipo": total_equipo,
        "total_alumnos": total_alumnos,
        "sugeridos_elegibles": sugeridos_elegibles,
        "sugeridos_faltan": sugeridos_faltan,
        "sugeridos_sobran": sugeridos_sobran,
        "sugeridos_stats": sugeridos_stats,
    })


# =============================================================================
# CICLOS
# =============================================================================

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