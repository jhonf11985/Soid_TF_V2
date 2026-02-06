from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count
from django.contrib import messages

from .models import ProgramaEducativo, CicloPrograma, GrupoFormativo, InscripcionGrupo
from .forms import ProgramaEducativoForm, CicloProgramaForm
from miembros_app.models import Miembro
from .utils_reglas import reporte_reglas_grupo
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import RolFormativo
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
    maestros = RolFormativo.objects.filter(
        tipo=RolFormativo.TIPO_MAESTRO,
        activo=True
    ).select_related("miembro")

    ayudantes = RolFormativo.objects.filter(
        tipo=RolFormativo.TIPO_AYUDANTE,
        activo=True
    ).select_related("miembro")

    return render(request, "formacion_app/programa_form.html", {
        "form": form,
        "programa": None,
            "maestros_disponibles": maestros,
    "ayudantes_disponibles": ayudantes,
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

    maestros = RolFormativo.objects.filter(
        tipo=RolFormativo.TIPO_MAESTRO,
        activo=True
    ).select_related("miembro")

    ayudantes = RolFormativo.objects.filter(
        tipo=RolFormativo.TIPO_AYUDANTE,
        activo=True
    ).select_related("miembro")        

    return render(request, "formacion_app/programa_form.html", {
        "form": form,
        "programa": programa,
            "maestros_disponibles": maestros,
    "ayudantes_disponibles": ayudantes,
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

    hoy = timezone.localdate()

    # Mapa: { grupo_id: SesionGrupo de hoy }
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

# Agregar esta vista a views.py de formacion_app

from django.shortcuts import render
from django.db.models import Count
from .models import ProgramaEducativo, GrupoFormativo
from .utils_reglas import reporte_reglas_grupo


def grupos_reporte(request):
    """
    Reporte de análisis de grupos formativos.
    """
    from django.db.models import Count
    
    grupos_qs = (
        GrupoFormativo.objects
        .select_related("programa")
        .prefetch_related("maestros", "ayudantes", "inscripciones")
        .annotate(total_alumnos=Count("inscripciones", distinct=True))
        .order_by("nombre")
    )
    
    grupos_data = []
    stats = {
        'total_grupos': 0,
        'grupos_con_faltantes': 0,
        'grupos_con_sobrantes': 0,
        'grupos_excedidos': 0,
        'grupos_sin_maestro': 0,
        'grupos_vacios': 0,
    }
    
    def miembro_to_dict(m):
        return {
            'id': m.id,
            'nombre': f"{m.nombres} {m.apellidos}".strip(),
            'codigo': getattr(m, 'codigo_miembro', '') or '',
        }
    
    for grupo in grupos_qs:
        stats['total_grupos'] += 1
        
        reporte = reporte_reglas_grupo(grupo)
        
        inscritos = [miembro_to_dict(m) for m in reporte['inscritos'][:50]]
        faltan = [miembro_to_dict(m) for m in reporte['faltan'][:50]]
        sobran = [miembro_to_dict(m) for m in reporte['sobran'][:50]]
        
        total_inscritos = reporte['inscritos'].count()
        total_faltan = reporte['faltan'].count()
        total_sobran = reporte['sobran'].count()
        
        excedido = False
        if grupo.cupo and total_inscritos > grupo.cupo:
            excedido = True
            stats['grupos_excedidos'] += 1
        
        sin_maestro = not grupo.maestros.exists()
        if sin_maestro:
            stats['grupos_sin_maestro'] += 1
        
        if total_inscritos == 0:
            stats['grupos_vacios'] += 1
        
        if total_faltan > 0:
            stats['grupos_con_faltantes'] += 1
        
        if total_sobran > 0:
            stats['grupos_con_sobrantes'] += 1
        
        grupos_data.append({
            'grupo': grupo,
            'inscritos': inscritos,
            'faltan': faltan,
            'sobran': sobran,
            'total_inscritos': total_inscritos,
            'total_faltan': total_faltan,
            'total_sobran': total_sobran,
            'excedido': excedido,
            'sin_maestro': sin_maestro,
        })
    
    programas = ProgramaEducativo.objects.filter(activo=True).order_by("nombre")
        
    # TOTAL miembros que pertenecen a la iglesia (NO es estado_miembro)
    total_miembros = Miembro.objects.filter(activo=True).count()

    # Miembros que están en al menos 1 grupo con inscripción ACTIVA
    miembros_con_grupo = (
        Miembro.objects
        .filter(
            activo=True,
            inscripciones_formacion__estado="ACTIVO",
            inscripciones_formacion__grupo__activo=True,  # recomendado
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

from django.http import HttpResponse


from .models import GrupoFormativo, SesionGrupo


def grupo_sesion_abrir(request, grupo_id):
    grupo = get_object_or_404(GrupoFormativo, pk=grupo_id)
    hoy = timezone.localdate()

    sesion, created = SesionGrupo.objects.get_or_create(
        grupo=grupo,
        fecha=hoy,
        defaults={
            "estado": SesionGrupo.ESTADO_ABIERTA,
            "inicio": timezone.now(),
            "creada_por": request.user if request.user.is_authenticated else None,
        },
    )

    # Si ya existía pero estaba cerrada → reabrimos
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

    # 👉 SIEMPRE vamos al detalle de la sesión
    return redirect("formacion:sesion_detalle", sesion_id=sesion.id)

def sesion_detalle(request, sesion_id):
    sesion = get_object_or_404(SesionGrupo, id=sesion_id)
    grupo = sesion.grupo

    asistencias = sesion.asistencias.select_related("miembro").order_by("marcado_en")

    # ✅ contar inscritos del grupo desde InscripcionGrupo
    total_grupo = InscripcionGrupo.objects.filter(grupo=grupo, estado="ACTIVO").count()

    return render(request, "formacion_app/sesion_detalle.html", {
        "sesion": sesion,
        "grupo": grupo,
        "asistencias": asistencias,
        "total_grupo": total_grupo,
    })

def sesion_kiosko(request, sesion_id):
    sesion = get_object_or_404(SesionGrupo, id=sesion_id)

    return render(request, "formacion_app/sesion_kiosko.html", {
        "sesion": sesion,
        "grupo": sesion.grupo,
    })

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import SesionGrupo, AsistenciaSesion, InscripcionGrupo
from miembros_app.models import Miembro


@require_POST
def sesion_kiosko_marcar(request, sesion_id):
    sesion = get_object_or_404(SesionGrupo, id=sesion_id)

    if sesion.estado != "ABIERTA":
        return JsonResponse({"ok": False, "msg": "Esta sesión está cerrada."}, status=400)

    codigo = (request.POST.get("codigo") or "").strip().upper()

    if not codigo:
        return JsonResponse({"ok": False, "msg": "Introduce el código."}, status=400)

    # Normaliza: si viene "0001" lo convertimos a "TF-0001"
    if codigo.isdigit():
        codigo = f"TF-{codigo.zfill(4)}"
    elif codigo.startswith("TF") and "-" not in codigo:
        # por si escriben TF0001
        num = codigo.replace("TF", "").strip()
        if num.isdigit():
            codigo = f"TF-{num.zfill(4)}"

    try:
        miembro = Miembro.objects.get(codigo_miembro=codigo)
    except Miembro.DoesNotExist:
        return JsonResponse({"ok": False, "msg": f"Código inválido: {codigo}"}, status=404)

    # Verificar que pertenece al grupo y está ACTIVO
    pertenece = InscripcionGrupo.objects.filter(
        grupo=sesion.grupo,
        miembro=miembro,
        estado="ACTIVO"
    ).exists()

    if not pertenece:
        return JsonResponse({"ok": False, "msg": "Este miembro no pertenece a este grupo."}, status=403)

    asistencia, created = AsistenciaSesion.objects.get_or_create(
        sesion=sesion,
        miembro=miembro,
        defaults={"metodo": "KIOSKO"}
    )

    if not created:
        return JsonResponse({"ok": False, "msg": "Ya estaba marcado hoy ✅"}, status=200)

    return JsonResponse({
        "ok": True,
        "msg": f"Asistencia registrada ✅ ({miembro.nombres} {miembro.apellidos})",
        "codigo": codigo,
        "marcado_en": timezone.localtime(asistencia.marcado_en).strftime("%d/%m/%Y %H:%M"),
    })

from django.views.decorators.http import require_POST

@require_POST
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
def roles_formativos(request):
    maestros = RolFormativo.objects.filter(tipo="MAESTRO")
    ayudantes = RolFormativo.objects.filter(tipo="AYUDANTE")

    return render(request, "formacion_app/roles_formativos.html", {
        "maestros": maestros,
        "ayudantes": ayudantes,
    })


@login_required
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

        miembro = None
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


@login_required
@require_POST
def rol_formativo_toggle(request, pk):
    rol = get_object_or_404(RolFormativo, pk=pk)
    rol.activo = not rol.activo
    rol.save(update_fields=["activo"])
    return redirect("formacion:roles_formativos")