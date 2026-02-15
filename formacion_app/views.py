from datetime import date
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from miembros_app.models import Miembro
from .forms import ProgramaEducativoForm, CicloProgramaForm
from .models import (
    ProgramaEducativo,
    CicloPrograma,
    GrupoFormativo,
    InscripcionGrupo,
    RolFormativo,
    SesionGrupo,
    AsistenciaSesion,
)
from .utils_reglas import reporte_reglas_grupo


# =============================================================================
# DASHBOARD
# =============================================================================

@login_required
def inicio_formacion(request):
    """
    Dashboard principal del módulo de formación.
    - Si el usuario tiene un Miembro asociado y es maestro de algún grupo activo:
      lo enviamos al Inicio del Maestro.
    - Si no es maestro: se queda en el dashboard con métricas.
    """
    miembro = getattr(request.user, "miembro", None)

    if miembro:
        es_maestro = GrupoFormativo.objects.filter(maestros=miembro, activo=True).exists()
        if es_maestro:
            return redirect("formacion:inicio_maestro")

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

@login_required
@permission_required('formacion_app.view_programaeducativo', raise_exception=True)
def programas_list(request):
    """Listado de todos los programas educativos."""
    programas = ProgramaEducativo.objects.all()
    return render(request, "formacion_app/programas_list.html", {"programas": programas})


@login_required
@permission_required('formacion_app.add_programaeducativo', raise_exception=True)
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

    maestros = (
        RolFormativo.objects
        .filter(tipo=RolFormativo.TIPO_MAESTRO, activo=True)
        .select_related("miembro")
    )
    ayudantes = (
        RolFormativo.objects
        .filter(tipo=RolFormativo.TIPO_AYUDANTE, activo=True)
        .select_related("miembro")
    )

    return render(request, "formacion_app/programa_form.html", {
        "form": form,
        "programa": None,
        "maestros_disponibles": maestros,
        "ayudantes_disponibles": ayudantes,
    })


@login_required
@permission_required('formacion_app.change_programaeducativo', raise_exception=True)
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

    maestros = (
        RolFormativo.objects
        .filter(tipo=RolFormativo.TIPO_MAESTRO, activo=True)
        .select_related("miembro")
    )
    ayudantes = (
        RolFormativo.objects
        .filter(tipo=RolFormativo.TIPO_AYUDANTE, activo=True)
        .select_related("miembro")
    )

    return render(request, "formacion_app/programa_form.html", {
        "form": form,
        "programa": programa,
        "maestros_disponibles": maestros,
        "ayudantes_disponibles": ayudantes,
    })


# =============================================================================
# GRUPOS / CLASES
# =============================================================================

@login_required
@permission_required('formacion_app.view_grupoformativo', raise_exception=True)
def grupos_listado(request):
    """Listado de grupos formativos."""
    grupos = (
        GrupoFormativo.objects
        .select_related("programa")
        .prefetch_related("maestros", "ayudantes")
        .annotate(total_alumnos=Count("inscripciones", distinct=True))
        .order_by("nombre")
    )

    hoy = timezone.localdate()

    sesiones_hoy = {
        s.grupo_id: s
        for s in SesionGrupo.objects.filter(
            grupo_id__in=grupos.values_list("id", flat=True),
            fecha=hoy,
        ).only("id", "grupo_id", "estado", "fecha")
    }

    return render(request, "formacion_app/grupos_list.html", {
        "grupos": grupos,
        "sesiones_hoy": sesiones_hoy,
        "hoy": hoy,
    })


def _parse_ids(ids_string: str):
    """Convierte string de IDs separados por coma a lista de enteros."""
    if not ids_string:
        return []
    return [int(x.strip()) for x in ids_string.split(",") if x.strip().isdigit()]


def _get_miembros_data(miembros_queryset):
    """Convierte queryset de miembros a lista de diccionarios para el template."""
    return [
        {
            "id": m.id,
            "nombre": f"{m.nombres} {m.apellidos}".strip(),
            "codigo": m.codigo_miembro or "",
        }
        for m in miembros_queryset
    ]


@login_required
@permission_required('formacion_app.add_grupoformativo', raise_exception=True)
def grupo_crear(request):
    """Crear un nuevo grupo/clase."""
    if request.method == "POST":
        try:
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

            maestros_ids = _parse_ids(request.POST.get("maestros_ids", ""))
            if maestros_ids:
                grupo.maestros.set(Miembro.objects.filter(id__in=maestros_ids))

            ayudantes_ids = _parse_ids(request.POST.get("ayudantes_ids", ""))
            if ayudantes_ids:
                grupo.ayudantes.set(Miembro.objects.filter(id__in=ayudantes_ids))

            estudiantes_ids = _parse_ids(request.POST.get("estudiantes_ids", ""))
            for miembro_id in estudiantes_ids:
                InscripcionGrupo.objects.get_or_create(
                    miembro_id=miembro_id,
                    grupo=grupo,
                    defaults={"estado": "ACTIVO"},
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
    return render(request, "formacion_app/grupo_form.html", {"grupo": None, "programas": programas})


@login_required
@permission_required('formacion_app.change_grupoformativo', raise_exception=True)
def grupo_editar(request, pk):
    """Editar un grupo/clase existente."""
    grupo = get_object_or_404(GrupoFormativo, pk=pk)

    if request.method == "POST":
        try:
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

            maestros_ids = _parse_ids(request.POST.get("maestros_ids", ""))
            grupo.maestros.set(Miembro.objects.filter(id__in=maestros_ids))

            ayudantes_ids = _parse_ids(request.POST.get("ayudantes_ids", ""))
            grupo.ayudantes.set(Miembro.objects.filter(id__in=ayudantes_ids))

            estudiantes_ids_nuevos = set(_parse_ids(request.POST.get("estudiantes_ids", "")))
            estudiantes_ids_actuales = set(
                grupo.inscripciones.filter(estado="ACTIVO").values_list("miembro_id", flat=True)
            )

            for miembro_id in estudiantes_ids_nuevos - estudiantes_ids_actuales:
                InscripcionGrupo.objects.get_or_create(
                    miembro_id=miembro_id,
                    grupo=grupo,
                    defaults={"estado": "ACTIVO"},
                )

            for miembro_id in estudiantes_ids_actuales - estudiantes_ids_nuevos:
                InscripcionGrupo.objects.filter(
                    miembro_id=miembro_id,
                    grupo=grupo,
                ).update(estado="RETIRADO")

            messages.success(request, "Grupo actualizado exitosamente.")
            return redirect("formacion:grupo_editar", pk=grupo.pk)

        except Exception:
            # Si hay error, seguimos al render con datos actuales
            pass

    programas = ProgramaEducativo.objects.filter(activo=True).order_by("nombre")

    maestros_actuales = _get_miembros_data(grupo.maestros.all())
    ayudantes_actuales = _get_miembros_data(grupo.ayudantes.all())

    estudiantes_qs = Miembro.objects.filter(
        inscripciones_formacion__grupo=grupo,
        inscripciones_formacion__estado="ACTIVO",
    )
    estudiantes_actuales = _get_miembros_data(estudiantes_qs)

    total_equipo = len(maestros_actuales) + len(ayudantes_actuales)
    total_alumnos = len(estudiantes_actuales)

    reporte = reporte_reglas_grupo(grupo)
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

@login_required
@permission_required('formacion_app.add_cicloprograma', raise_exception=True)
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

    return render(request, "formacion_app/ciclo_form.html", {"form": form, "ciclo": None})


@login_required
@permission_required('formacion_app.change_cicloprograma', raise_exception=True)
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

    return render(request, "formacion_app/ciclo_form.html", {"form": form, "ciclo": ciclo})


# =============================================================================
# REPORTES
# =============================================================================

@login_required
@permission_required('formacion_app.view_grupoformativo', raise_exception=True)
def grupos_reporte(request):
    """
    Reporte de análisis de grupos formativos.
    """
    grupos_qs = (
        GrupoFormativo.objects
        .select_related("programa")
        .prefetch_related("maestros", "ayudantes", "inscripciones")
        .annotate(total_alumnos=Count("inscripciones", distinct=True))
        .order_by("nombre")
    )

    def miembro_to_dict(m):
        return {
            "id": m.id,
            "nombre": f"{m.nombres} {m.apellidos}".strip(),
            "codigo": getattr(m, "codigo_miembro", "") or "",
        }

    grupos_data = []
    stats = {
        "total_grupos": 0,
        "grupos_con_faltantes": 0,
        "grupos_con_sobrantes": 0,
        "grupos_excedidos": 0,
        "grupos_sin_maestro": 0,
        "grupos_vacios": 0,
    }

    for grupo in grupos_qs:
        stats["total_grupos"] += 1

        reporte = reporte_reglas_grupo(grupo)

        inscritos = [miembro_to_dict(m) for m in reporte["inscritos"][:50]]
        faltan = [miembro_to_dict(m) for m in reporte["faltan"][:50]]
        sobran = [miembro_to_dict(m) for m in reporte["sobran"][:50]]

        total_inscritos = reporte["inscritos"].count()
        total_faltan = reporte["faltan"].count()
        total_sobran = reporte["sobran"].count()

        excedido = bool(grupo.cupo and total_inscritos > grupo.cupo)
        if excedido:
            stats["grupos_excedidos"] += 1

        sin_maestro = not grupo.maestros.exists()
        if sin_maestro:
            stats["grupos_sin_maestro"] += 1

        if total_inscritos == 0:
            stats["grupos_vacios"] += 1

        if total_faltan > 0:
            stats["grupos_con_faltantes"] += 1

        if total_sobran > 0:
            stats["grupos_con_sobrantes"] += 1

        grupos_data.append({
            "grupo": grupo,
            "inscritos": inscritos,
            "faltan": faltan,
            "sobran": sobran,
            "total_inscritos": total_inscritos,
            "total_faltan": total_faltan,
            "total_sobran": total_sobran,
            "excedido": excedido,
            "sin_maestro": sin_maestro,
        })

    programas = ProgramaEducativo.objects.filter(activo=True).order_by("nombre")

    total_miembros = Miembro.objects.filter(activo=True).count()
    miembros_con_grupo = (
        Miembro.objects
        .filter(
            activo=True,
            inscripciones_formacion__estado="ACTIVO",
            inscripciones_formacion__grupo__activo=True,
        )
        .distinct()
        .count()
    )
    miembros_sin_grupo = total_miembros - miembros_con_grupo
    porc_sin_grupo = round((miembros_sin_grupo / total_miembros) * 100, 2) if total_miembros else 0

    stats["total_miembros_iglesia"] = total_miembros
    stats["miembros_sin_grupo"] = miembros_sin_grupo
    stats["porc_sin_grupo"] = porc_sin_grupo

    return render(request, "formacion_app/grupos_reporte.html", {
        "grupos": grupos_data,
        "stats": stats,
        "programas": programas,
    })


def _estado_programa(grupos_total, pct_alerta, cobertura):
    """
    Semáforo simple (v1):
    - 🔴 Riesgo: muchos grupos con alertas o muy baja cobertura
    - 🟡 Observación: algo de alerta o cobertura baja
    - 🟢 Saludable: estable
    """
    if grupos_total == 0:
        return ("riesgo", "sin_grupos")

    if pct_alerta > 40 or cobertura < 10:
        return ("riesgo", "alertas_altas" if pct_alerta > 40 else "cobertura_baja")

    if pct_alerta >= 15 or cobertura < 20:
        return ("observacion", "alertas_medias" if pct_alerta >= 15 else "cobertura_media")

    return ("saludable", "ok")


@login_required
@permission_required('formacion_app.view_programaeducativo', raise_exception=True)
def reporte_analisis_programas(request):
    total_iglesia = Miembro.objects.filter(activo=True).count()
    programas = ProgramaEducativo.objects.filter(activo=True).order_by("nombre")

    items = []
    for p in programas:
        qs_grupos = GrupoFormativo.objects.filter(programa=p)

        grupos_total = qs_grupos.count()
        grupos_activos = qs_grupos.filter(activo=True).count()
        grupos_inactivos = grupos_total - grupos_activos

        grupos_sin_maestro = (
            qs_grupos
            .filter(maestros__isnull=True, maestro__isnull=True)
            .distinct()
            .count()
        )

        grupos_vacios = (
            qs_grupos
            .annotate(
                total_activos=Count(
                    "inscripciones",
                    filter=Q(
                        inscripciones__estado="ACTIVO",
                        inscripciones__miembro__activo=True,
                    ),
                    distinct=True,
                )
            )
            .filter(total_activos=0)
            .count()
        )

        miembros_inscritos = (
            InscripcionGrupo.objects
            .filter(
                grupo__programa=p,
                estado="ACTIVO",
                miembro__activo=True,
                grupo__activo=True,
            )
            .values("miembro_id")
            .distinct()
            .count()
        )

        cobertura = round((miembros_inscritos / total_iglesia) * 100, 2) if total_iglesia else 0
        alertas = grupos_sin_maestro + grupos_vacios
        pct_alerta = round((alertas / grupos_total) * 100, 2) if grupos_total else 0

        estado, motivo = _estado_programa(grupos_total, pct_alerta, cobertura)

        grupos_detalle = (
            qs_grupos
            .annotate(
                inscritos=Count(
                    "inscripciones",
                    filter=Q(
                        inscripciones__estado="ACTIVO",
                        inscripciones__miembro__activo=True,
                    ),
                    distinct=True,
                )
            )
            .order_by("nombre")
        )

        items.append({
            "programa": p,
            "grupos_total": grupos_total,
            "grupos_activos": grupos_activos,
            "grupos_inactivos": grupos_inactivos,
            "grupos_sin_maestro": grupos_sin_maestro,
            "grupos_vacios": grupos_vacios,
            "miembros_inscritos": miembros_inscritos,
            "cobertura": cobertura,
            "pct_alerta": pct_alerta,
            "estado": estado,
            "motivo": motivo,
            "grupos_detalle": grupos_detalle,
        })

    total_programas = len(items)
    saludables = sum(1 for i in items if i["estado"] == "saludable")
    observacion = sum(1 for i in items if i["estado"] == "observacion")
    riesgo = sum(1 for i in items if i["estado"] == "riesgo")

    cobertura_prom = round(
        (sum(i["cobertura"] for i in items) / total_programas), 2
    ) if total_programas else 0

    stats = {
        "total_programas": total_programas,
        "saludables": saludables,
        "observacion": observacion,
        "riesgo": riesgo,
        "total_iglesia": total_iglesia,
        "cobertura_prom": cobertura_prom,
    }

    return render(request, "formacion_app/programas_reporte.html", {
        "stats": stats,
        "items": items,
    })


# =============================================================================
# SESIONES (ABRIR / DETALLE / KIOSKO)
# =============================================================================

@login_required
@permission_required('formacion_app.add_sesiongrupo', raise_exception=True)
def grupo_sesion_abrir(request, grupo_id):
    grupo = get_object_or_404(GrupoFormativo, pk=grupo_id)
    hoy = timezone.localdate()

    sesion, created = SesionGrupo.objects.get_or_create(
        grupo=grupo,
        fecha=hoy,
        defaults={
            "estado": SesionGrupo.ESTADO_ABIERTA,
            "inicio": timezone.now(),
            "creada_por": request.user,
        },
    )

    if not created and sesion.estado == SesionGrupo.ESTADO_CERRADA:
        sesion.estado = SesionGrupo.ESTADO_ABIERTA
        sesion.inicio = timezone.now()
        sesion.fin = None
        sesion.save(update_fields=["estado", "inicio", "fin"])
        messages.success(request, "Sesión reabierta correctamente.")
    elif created:
        messages.success(request, "Sesión abierta correctamente.")
    else:
        messages.info(request, "Ya existe una sesión abierta para hoy.")

    return redirect("formacion:sesion_detalle", sesion_id=sesion.id)


@login_required
@permission_required('formacion_app.view_sesiongrupo', raise_exception=True)
def sesion_detalle(request, sesion_id):
    sesion = get_object_or_404(SesionGrupo, id=sesion_id)
    grupo = sesion.grupo

    asistencias = sesion.asistencias.select_related("miembro").order_by("marcado_en")
    total_grupo = InscripcionGrupo.objects.filter(grupo=grupo, estado="ACTIVO").count()

    return render(request, "formacion_app/sesion_detalle.html", {
        "sesion": sesion,
        "grupo": grupo,
        "asistencias": asistencias,
        "total_grupo": total_grupo,
    })


@login_required
@permission_required('formacion_app.view_sesiongrupo', raise_exception=True)
def sesion_kiosko(request, sesion_id):
    sesion = get_object_or_404(SesionGrupo, id=sesion_id)
    return render(request, "formacion_app/sesion_kiosko.html", {
        "sesion": sesion,
        "grupo": sesion.grupo,
    })


@require_POST
@login_required
@permission_required('formacion_app.add_asistenciasesion', raise_exception=True)
def sesion_kiosko_marcar(request, sesion_id):
    sesion = get_object_or_404(SesionGrupo, id=sesion_id)

    if sesion.estado != "ABIERTA":
        return JsonResponse({"ok": False, "msg": "Esta sesión está cerrada."}, status=400)

    codigo = (request.POST.get("codigo") or "").strip().upper()
    if not codigo:
        return JsonResponse({"ok": False, "msg": "Introduce el código."}, status=400)

    if codigo.isdigit():
        codigo = f"TF-{codigo.zfill(4)}"
    elif codigo.startswith("TF") and "-" not in codigo:
        num = codigo.replace("TF", "").strip()
        if num.isdigit():
            codigo = f"TF-{num.zfill(4)}"

    try:
        miembro = Miembro.objects.get(codigo_miembro=codigo)
    except Miembro.DoesNotExist:
        return JsonResponse({"ok": False, "msg": f"Código inválido: {codigo}"}, status=404)

    pertenece = InscripcionGrupo.objects.filter(
        grupo=sesion.grupo,
        miembro=miembro,
        estado="ACTIVO",
    ).exists()

    if not pertenece:
        return JsonResponse({"ok": False, "msg": "Este miembro no pertenece a este grupo."}, status=403)

    asistencia, created = AsistenciaSesion.objects.get_or_create(
        sesion=sesion,
        miembro=miembro,
        defaults={"metodo": "KIOSKO"},
    )

    if not created:
        return JsonResponse({"ok": False, "msg": "Ya estaba marcado hoy ✅"}, status=200)

    return JsonResponse({
        "ok": True,
        "msg": f"Asistencia registrada ✅ ({miembro.nombres} {miembro.apellidos})",
        "codigo": codigo,
        "marcado_en": timezone.localtime(asistencia.marcado_en).strftime("%d/%m/%Y %H:%M"),
        "nombre": f"{miembro.nombres} {miembro.apellidos}".strip(),
        "grupo": sesion.grupo.nombre,
    })


@require_POST
@login_required
@permission_required('formacion_app.change_sesiongrupo', raise_exception=True)
def sesion_cerrar(request, sesion_id):
    sesion = get_object_or_404(SesionGrupo, id=sesion_id)

    if sesion.estado != SesionGrupo.ESTADO_ABIERTA:
        messages.info(request, "Esta sesión ya estaba cerrada.")
        return redirect("formacion:sesion_detalle", sesion_id=sesion.id)

    sesion.estado = SesionGrupo.ESTADO_CERRADA
    sesion.fin = timezone.now()
    sesion.save(update_fields=["estado", "fin"])

    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("formacion:grupos")


# =============================================================================
# ROLES FORMATIVOS (MAESTROS / AYUDANTES)
# =============================================================================

@login_required
@permission_required('formacion_app.view_rolformativo', raise_exception=True)
def roles_formativos(request):
    maestros = (
        RolFormativo.objects
        .select_related("miembro")
        .filter(tipo=RolFormativo.TIPO_MAESTRO)
        .order_by("-activo", "miembro__nombres", "miembro__apellidos")
    )
    ayudantes = (
        RolFormativo.objects
        .select_related("miembro")
        .filter(tipo=RolFormativo.TIPO_AYUDANTE)
        .order_by("-activo", "miembro__nombres", "miembro__apellidos")
    )

    return render(request, "formacion_app/roles_formativos.html", {
        "maestros": maestros,
        "ayudantes": ayudantes,
        "total_maestros": maestros.count(),
        "total_ayudantes": ayudantes.count(),
    })


@login_required
@permission_required('formacion_app.add_rolformativo', raise_exception=True)
def rol_formativo_nuevo(request):
    """
    Crea un rol formativo (MAESTRO o AYUDANTE) para un miembro.
    Usamos un input hidden con miembro_id para que sea simple.
    """
    if request.method == "POST":
        miembro_id = request.POST.get("miembro_id") or ""
        tipo = request.POST.get("tipo") or ""

        errores = []
        if not miembro_id.isdigit():
            errores.append("Selecciona un miembro válido.")
        if tipo not in (RolFormativo.TIPO_MAESTRO, RolFormativo.TIPO_AYUDANTE):
            errores.append("Selecciona un tipo válido (Maestro o Ayudante).")

        if not errores:
            miembro = get_object_or_404(Miembro, pk=int(miembro_id))

            obj, created = RolFormativo.objects.get_or_create(
                miembro=miembro,
                tipo=tipo,
                defaults={"activo": True},
            )

            if not created and not obj.activo:
                obj.activo = True
                obj.save(update_fields=["activo"])

            messages.success(request, "Rol guardado correctamente.")
            return redirect("formacion:roles_formativos")

        return render(request, "formacion_app/rol_formativo_form.html", {
            "errores": "\n".join(errores),
            "tipos": [RolFormativo.TIPO_MAESTRO, RolFormativo.TIPO_AYUDANTE],
        })

    return render(request, "formacion_app/rol_formativo_form.html", {
        "tipos": [RolFormativo.TIPO_MAESTRO, RolFormativo.TIPO_AYUDANTE],
    })


@require_POST
@login_required
@permission_required('formacion_app.change_rolformativo', raise_exception=True)
def rol_formativo_toggle(request, pk):
    rol = get_object_or_404(RolFormativo, pk=pk)
    rol.activo = not rol.activo
    rol.save(update_fields=["activo"])
    return redirect("formacion:roles_formativos")


# =============================================================================
# INICIO MAESTRO
# =============================================================================

def _user_to_miembro(user):
    return getattr(user, "miembro", None)



@login_required
def inicio_maestro_formacion(request):
    miembro = _user_to_miembro(request.user)
    if not miembro:
        return redirect("formacion:inicio")

    grupos = (
        GrupoFormativo.objects
        .filter(maestros=miembro, activo=True)
        .prefetch_related("maestros", "ayudantes")
        .order_by("nombre")
    )

    if not grupos.exists():
        return redirect("formacion:inicio")

    hoy = timezone.localdate()
    ahora = timezone.localtime()
    hora = ahora.hour

    # Saludo “humano”
    if 5 <= hora < 12:
        saludo = "Buenos días"
        icono = "wb_sunny"
    elif 12 <= hora < 18:
        saludo = "Buenas tardes"
        icono = "light_mode"
    else:
        saludo = "Buenas noches"
        icono = "dark_mode"

    nombre_usuario = (
        (getattr(request.user, "first_name", "") or request.user.get_username()).strip()
        or "Maestro"
    )

    grupo_cards = []

    total_grupos = 0
    sesiones_creadas = 0
    sesiones_abiertas = 0
    faltantes_total = 0
    sobran_total = 0
    ausentes_regulares_total = 0

    for g in grupos:
        total_grupos += 1

        total = InscripcionGrupo.objects.filter(grupo=g, estado="ACTIVO").count()

        faltan_count = 0
        sobran_count = 0
        try:
            rep = reporte_reglas_grupo(g)
            faltan_count = rep["faltan"].count()
            sobran_count = rep["sobran"].count()
        except Exception:
            # Si algo falla, no rompemos la pantalla
            faltan_count = 0
            sobran_count = 0

        faltantes_total += faltan_count
        sobran_total += sobran_count

        sesion_hoy = SesionGrupo.objects.filter(grupo=g, fecha=hoy).order_by("-id").first()
        sesion_hoy_id = sesion_hoy.id if sesion_hoy else None
        sesion_hoy_estado = sesion_hoy.estado if sesion_hoy else None

        if sesion_hoy:
            sesiones_creadas += 1
            if sesion_hoy_estado == "ABIERTA":
                sesiones_abiertas += 1

        # Detectar estudiantes regulares con ausencias recientes (últimas 3 sesiones)
        ausentes_regulares = []
        
        # Obtener últimas 3 sesiones del grupo (sin contar hoy)
        ultimas_sesiones = (
            SesionGrupo.objects
            .filter(grupo=g, fecha__lt=hoy)
            .order_by("-fecha")[:3]
        )
        
        if ultimas_sesiones.exists() and ultimas_sesiones.count() >= 3:
            # Obtener inscritos activos
            inscritos = InscripcionGrupo.objects.filter(grupo=g, estado="ACTIVO").select_related("miembro")
            
            for inscrito in inscritos:
                # Calcular asistencia histórica total (sin contar las últimas 3)
                todas_sesiones = SesionGrupo.objects.filter(grupo=g, fecha__lt=hoy).exclude(
                    id__in=ultimas_sesiones.values_list("id", flat=True)
                )
                
                if todas_sesiones.exists() and todas_sesiones.count() >= 5:
                    total_sesiones_historicas = todas_sesiones.count()
                    asistencias_historicas = AsistenciaSesion.objects.filter(
                        sesion__in=todas_sesiones,
                        inscripcion=inscrito,
                        presente=True
                    ).count()
                    
                    # Si tiene >= 70% de asistencia histórica, es "regular"
                    porcentaje_asistencia = (asistencias_historicas / total_sesiones_historicas) * 100
                    
                    if porcentaje_asistencia >= 70:
                        # Verificar ausencias en las últimas 3 sesiones
                        ausencias_recientes = 0
                        for sesion in ultimas_sesiones:
                            asistio = AsistenciaSesion.objects.filter(
                                sesion=sesion,
                                inscripcion=inscrito,
                                presente=True
                            ).exists()
                            if not asistio:
                                ausencias_recientes += 1
                        
                        # Si faltó a 2 o más de las últimas 3 sesiones
                        if ausencias_recientes >= 2:
                            ausentes_regulares.append({
                                "nombre": f"{inscrito.miembro.nombres} {inscrito.miembro.apellidos}",
                                "ausencias": ausencias_recientes
                            })
        
        ausentes_regulares_count = len(ausentes_regulares)
        ausentes_regulares_total += ausentes_regulares_count

        # Mensajes IA por grupo (el sistema "te habla")
        mensajes = []

        if ausentes_regulares_count > 0:
            nombres_ausentes = ", ".join([a["nombre"] for a in ausentes_regulares[:3]])
            if ausentes_regulares_count > 3:
                nombres_ausentes += f" y {ausentes_regulares_count - 3} más"
            
            mensajes.append({
                "texto": (
                    f"He notado que {nombres_ausentes} "
                    f"{'suele' if ausentes_regulares_count == 1 else 'suelen'} asistir, "
                    f"pero ha faltado a las últimas clases. Tal vez quieras contactarle para ver si todo está bien 🤔"
                ),
                "accion_texto": "Ver detalles del grupo",
                "accion_url_name": "formacion:grupo_editar",
                "accion_icono": "people",
            })

        if faltan_count > 0:
            mensajes.append({
                "texto": (
                    f"Hay {faltan_count} {'persona' if faltan_count == 1 else 'personas'} que por su perfil "
                    f"{'encaja' if faltan_count == 1 else 'encajan'} en este grupo pero no {'está inscrita' if faltan_count == 1 else 'están inscritas'}. "
                    f"Échale un ojo cuando puedas 😉"
                ),
                "accion_texto": "Ver quiénes son",
                "accion_url_name": "formacion:grupo_editar",
                "accion_icono": "person_add",
            })

        if sobran_count > 0:
            mensajes.append({
                "texto": (
                    f"Veo {sobran_count} {'inscrito' if sobran_count == 1 else 'inscritos'} que no "
                    f"{'cumple' if sobran_count == 1 else 'cumplen'} las reglas del grupo. "
                    f"No es urgente, pero conviene revisarlo cuando tengas un momento 😉"
                ),
                "accion_texto": "Revisar reglas",
                "accion_url_name": "formacion:grupo_editar",
                "accion_icono": "rule",
            })

        if not mensajes:
            mensajes.append({
                "texto": "Todo se ve perfecto aquí. No tengo ninguna alerta para esta clase ✅",
                "accion_texto": None,
                "accion_url_name": None,
                "accion_icono": None,
            })

        grupo_cards.append({
            "id": g.id,
            "nombre": g.nombre,
            "total": total,
            "sesion_hoy_id": sesion_hoy_id,
            "sesion_hoy_estado": sesion_hoy_estado,
            "mensajes": mensajes,
            "url_ajustar_grupo": reverse("formacion:grupo_editar", kwargs={"pk": g.id}),
            "url_ir_a_mi_clase": reverse("formacion:ir_a_mi_clase", kwargs={"grupo_id": g.id}),
        })

    pendientes_sesion = total_grupos - sesiones_creadas

    # Mensajes generales tipo IA (arriba)
    resumen = (
        f"Hoy tienes {total_grupos} {'clase' if total_grupos == 1 else 'clases'}. "
        f"Ya hay {sesiones_creadas} {'sesión creada' if sesiones_creadas == 1 else 'sesiones creadas'} "
        f"y {sesiones_abiertas} {'abierta' if sesiones_abiertas == 1 else 'abiertas'}."
    )

    mensajes_generales = []

    if pendientes_sesion > 0:
        mensajes_generales.append(
            f"Tienes {pendientes_sesion} {'clase' if pendientes_sesion == 1 else 'clases'} sin sesión creada hoy. "
            f"Si vas a impartirlas, puedes abrirlas desde aquí 😉"
        )

    if ausentes_regulares_total > 0:
        mensajes_generales.append(
            f"He detectado {ausentes_regulares_total} {'estudiante regular que ha' if ausentes_regulares_total == 1 else 'estudiantes regulares que han'} "
            f"faltado a las últimas clases. Podría ser buena idea contactarlos 🤝"
        )

    if faltantes_total > 0:
        mensajes_generales.append(
            f"Hay {faltantes_total} {'persona que encaja' if faltantes_total == 1 else 'personas que encajan'} por perfil en tus grupos "
            f"pero aún no {'está inscrita' if faltantes_total == 1 else 'están inscritas'}. Revísalo cuando puedas 😉"
        )

    if sobran_total > 0:
        mensajes_generales.append(
            f"También veo {sobran_total} {'persona inscrita' if sobran_total == 1 else 'personas inscritas'} que no "
            f"{'cumple' if sobran_total == 1 else 'cumplen'} las reglas. "
            f"No pasa nada, pero conviene ordenarlo cuando tengas un momento 😉"
        )

    if not mensajes_generales:
        mensajes_generales.append("Hoy todo pinta bien. Si solo vienes a dar clase, estás listo ✅")

    ctx = {
        "ia": {
            "saludo": saludo,
            "icono": icono,
            "nombre": nombre_usuario,
            "resumen": resumen,
            "mensajes": mensajes_generales,
        },
        "grupo_cards": grupo_cards,
        "hoy": hoy,
    }

    return render(request, "formacion_app/inicio_maestro.html", ctx)


@login_required
def ir_a_mi_clase(request, grupo_id):
    """
    Botón principal: crea/reutiliza sesión de HOY y redirige a sesion_detalle.
    Seguridad: solo si el usuario es maestro de ese grupo.
    """
    miembro = _user_to_miembro(request.user)
    grupo = get_object_or_404(GrupoFormativo, id=grupo_id)

    if not miembro or not GrupoFormativo.objects.filter(id=grupo.id, maestros=miembro, activo=True).exists():
        return redirect("formacion:inicio_maestro")

    hoy = timezone.localdate()

    sesion, created = SesionGrupo.objects.get_or_create(
        grupo=grupo,
        fecha=hoy,
        defaults={
            "estado": SesionGrupo.ESTADO_ABIERTA,
            "inicio": timezone.now(),
            "creada_por": request.user,
        },
    )

    if not created and sesion.estado == SesionGrupo.ESTADO_CERRADA:
        sesion.estado = SesionGrupo.ESTADO_ABIERTA
        sesion.inicio = timezone.now()
        sesion.fin = None
        sesion.save(update_fields=["estado", "inicio", "fin"])

    return redirect("formacion:sesion_detalle", sesion_id=sesion.id)

@login_required
@permission_required('formacion_app.view_grupoformativo', raise_exception=True)
def grupo_detalle(request, pk):
    grupo = get_object_or_404(
        GrupoFormativo.objects
        .select_related("programa")
        .prefetch_related("maestros", "ayudantes"),
        pk=pk
    )

    alumnos = (
        InscripcionGrupo.objects
        .filter(grupo=grupo, estado="ACTIVO")
        .select_related("miembro")
        .order_by("miembro__nombres")
    )

    sesiones = (
        SesionGrupo.objects
        .filter(grupo=grupo)
        .order_by("-fecha")[:10]
    )

    reporte = reporte_reglas_grupo(grupo)

    ctx = {
        "grupo": grupo,
        "alumnos": alumnos,
        "sesiones": sesiones,
        "stats": {
            "total_alumnos": alumnos.count(),
            "faltan": reporte["faltan"].count(),
            "sobran": reporte["sobran"].count(),
        }
    }

    return render(request, "formacion_app/grupo_detalle.html", ctx)


