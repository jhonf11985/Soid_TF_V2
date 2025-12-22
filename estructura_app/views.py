import json
from django import forms

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from miembros_app.models import Miembro
from .forms import UnidadForm, RolUnidadForm, ActividadUnidadForm, ReportePeriodoForm

from .models import (
    Unidad,
    TipoUnidad,
    RolUnidad,
    UnidadMembresia,
    UnidadCargo,
    ActividadUnidad,
    ReporteUnidadPeriodo,
)


# ============================================================
# HOME / DASHBOARD
# ============================================================

@login_required
def estructura_home(request):
    return render(request, "estructura_app/home.html")


@login_required
def dashboard(request):
    total_unidades = Unidad.objects.count()
    total_tipos = TipoUnidad.objects.filter(activo=True).count()
    total_roles = RolUnidad.objects.filter(activo=True).count()

    lideres_vigentes = UnidadCargo.objects.filter(
        vigente=True,
        rol__tipo=RolUnidad.TIPO_LIDERAZGO
    ).count()

    unidades_activas = Unidad.objects.filter(activa=True).count()
    unidades_inactivas = Unidad.objects.filter(activa=False).count()

    unidades_con_lider = UnidadCargo.objects.filter(
        vigente=True,
        rol__tipo=RolUnidad.TIPO_LIDERAZGO
    ).values_list("unidad_id", flat=True).distinct()

    unidades_sin_lider = Unidad.objects.filter(activa=True).exclude(id__in=unidades_con_lider).count()

    top_unidades = (
        Unidad.objects.annotate(
            total_miembros=Count("membresias", filter=Q(membresias__activo=True))
        )
        .order_by("-total_miembros", "nombre")[:6]
    )

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


# ============================================================
# UNIDADES
# ============================================================

@login_required
def unidad_crear(request):
    if request.method == "POST":
        form = UnidadForm(request.POST, request.FILES)
        if form.is_valid():
            unidad = form.save(commit=False)
            unidad.edad_min = _to_int_from_post(request.POST, "edad_min")
            unidad.edad_max = _to_int_from_post(request.POST, "edad_max")

            unidad.reglas = _reglas_mvp_from_post(request.POST)
            unidad.save()

            messages.success(request, "Unidad creada correctamente.")

            if request.POST.get("guardar_y_nuevo") == "1":
                return redirect("estructura_app:unidad_crear")

            return redirect("estructura_app:unidad_listado")
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

    bloqueada = unidad.esta_bloqueada

    if request.method == "POST":

        # 🔒 SI ESTÁ BLOQUEADA → SOLO GUARDAMOS IMAGEN
        if bloqueada:
            imagen = request.FILES.get("imagen")
            if imagen:
                unidad.imagen = imagen
                unidad.save(update_fields=["imagen", "actualizado_en"])
                messages.success(request, "Imagen actualizada correctamente.")
            else:
                messages.warning(request, "No se seleccionó ninguna imagen.")
            return redirect("estructura_app:unidad_editar", pk=unidad.pk)

        # 🔓 SI NO ESTÁ BLOQUEADA → EDICIÓN NORMAL
        form = UnidadForm(request.POST, request.FILES, instance=unidad)
        if form.is_valid():
            unidad_obj = form.save(commit=False)
            unidad_obj.edad_min = _to_int_from_post(request.POST, "edad_min")
            unidad_obj.edad_max = _to_int_from_post(request.POST, "edad_max")

            if any(k.startswith("regla_") for k in request.POST.keys()):
                unidad_obj.reglas = _reglas_mvp_from_post(request.POST)

            unidad_obj.save()
            messages.success(request, "Cambios guardados correctamente.")
            return redirect("estructura_app:unidad_listado")
        else:
            messages.error(request, "Revisa los campos marcados.")
    else:
        form = UnidadForm(instance=unidad)

    # ⚠️ MENSAJE CUANDO ESTÁ BLOQUEADA
    if bloqueada:
        messages.warning(
            request,
            "Esta unidad ya tiene miembros o cargos asignados. "
            "Solo puedes cambiar la imagen."
        )

    return render(request, "estructura_app/unidad_form.html", {
        "form": form,
        "modo": "editar",
        "unidad": unidad,
        "bloqueada": bloqueada,
    })



@login_required
def unidad_listado(request):
    query = request.GET.get("q", "").strip()

    unidades = (
        Unidad.objects
        .annotate(
            total_miembros=Count(
                "membresias",
                filter=Q(membresias__activo=True),
                distinct=True
            ),
            total_lideres=Count(
                "cargos",
                filter=Q(
                    cargos__vigente=True,
                    cargos__rol__tipo=RolUnidad.TIPO_LIDERAZGO
                ),
                distinct=True
            )
        )
        .order_by("nombre")
    )


    if query:
        unidades = unidades.filter(
            Q(nombre__icontains=query) | Q(codigo__icontains=query)
        )

    return render(request, "estructura_app/unidad_listado.html", {
        "unidades": unidades,
        "query": query,
    })

@login_required
def unidad_detalle(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)

    miembros_asignados = (
        UnidadMembresia.objects
        .filter(unidad=unidad, activo=True)
        .select_related("miembo_fk", "rol")
        .order_by("miembo_fk__nombres", "miembo_fk__apellidos")
    )

    # ✅ NUEVO: Equipo de trabajo (solo roles tipo TRABAJO)
    equipo_trabajo_asignados = (
        UnidadMembresia.objects
        .filter(
            unidad=unidad,
            activo=True,
            rol__tipo=RolUnidad.TIPO_TRABAJO
        )
        .select_related("miembo_fk", "rol")
        .order_by("rol__orden", "rol__nombre", "miembo_fk__nombres", "miembo_fk__apellidos")
    )

    lideres_asignados = (
        UnidadCargo.objects
        .filter(unidad=unidad, vigente=True)
        .select_related("miembo_fk", "rol")
        .order_by("rol__nombre", "miembo_fk__nombres", "miembo_fk__apellidos")
    )

    miembros = [m.miembo_fk for m in miembros_asignados]
    total = len(miembros)

    # --- Género: usa el display si existe (más fiable)
    masculinos = 0
    femeninos = 0
    for m in miembros:
        g = ""
        try:
            g = (m.get_genero_display() or "").strip().lower()
        except Exception:
            g = (getattr(m, "genero", "") or "").strip().lower()

        if g in ("m", "masculino", "hombre"):
            masculinos += 1
        elif g in ("f", "femenino", "mujer"):
            femeninos += 1

    # --- Estados (tu lógica: estado vacío = menor)
    activos = pasivos = observacion = disciplina = catecumenos = menores_estado_vacio = 0
    for m in miembros:
        e = (m.estado_miembro or "").strip().lower()
        if e == "":
            menores_estado_vacio += 1
        elif e == "activo":
            activos += 1
        elif e == "pasivo":
            pasivos += 1
        elif e == "observacion":
            observacion += 1
        elif e == "disciplina":
            disciplina += 1
        elif e == "catecumeno":
            catecumenos += 1

    # Menores/Mayores: principal por estado vacío (como tú definiste)
    menores = menores_estado_vacio
    mayores = total - menores

    # --- Categoría de edad (display)
    cat_map = {}
    for m in miembros:
        label = "—"
        try:
            label = m.get_categoria_edad_display() if m.categoria_edad else "—"
        except Exception:
            label = "—"
        cat_map[label] = cat_map.get(label, 0) + 1

    categorias_edad = [{"nombre": k, "total": v} for k, v in cat_map.items()]

    resumen = {
        "total": total,
        "masculinos": masculinos,
        "femeninos": femeninos,
        "menores": menores,
        "mayores": mayores,
        "activos": activos,
        "pasivos": pasivos,
        "observacion": observacion,
        "disciplina": disciplina,
        "catecumenos": catecumenos,
        "menores_estado_vacio": menores_estado_vacio,
        "categorias_edad": categorias_edad,
    }

    # =====================================================
    # CAPACIDAD MÁXIMA (solo para advertencia sutil en ficha)
    # =====================================================
    capacidad_maxima = None
    capacidad_excedida = False
    try:
        reglas = unidad.reglas or {}
        capacidad_maxima = reglas.get("capacidad_maxima", None)
        if capacidad_maxima is not None:
            capacidad_maxima = int(capacidad_maxima)
            capacidad_excedida = total >= capacidad_maxima
    except Exception:
        capacidad_maxima = None
        capacidad_excedida = False

    return render(request, "estructura_app/unidad_detalle.html", {
        "unidad": unidad,
        "miembros_asignados": miembros_asignados,
        "equipo_trabajo_asignados": equipo_trabajo_asignados,  # ✅ NUEVO
        "lideres_asignados": lideres_asignados,
        "resumen": resumen,

        "miembros_count": total,
        "capacidad_maxima": capacidad_maxima,
        "capacidad_excedida": capacidad_excedida,
    })



def _reglas_mvp_from_post(post):
    """
    Lee reglas MVP desde request.POST y devuelve un dict listo para guardar en JSONField.
    'solo_activos' bloquea todas las demás reglas de membresía.
    """

    def is_on(name, default=False):
        if name not in post:
            return default
        return post.get(name) in ("on", "1", "true", "True")

    def to_int(name, default=None):
        raw = (post.get(name) or "").strip()
        if raw == "":
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    solo_activos = is_on("regla_solo_activos", default=False)

    reglas = {
        "solo_activos": solo_activos,

        # ── Reglas de estado ──
        "permite_observacion": False if solo_activos else is_on("regla_perm_observacion"),
        "permite_pasivos": False if solo_activos else is_on("regla_perm_pasivos"),
        "permite_disciplina": False if solo_activos else is_on("regla_perm_disciplina"),
        "permite_catecumenos": False if solo_activos else is_on("regla_perm_catecumenos"),
        "permite_nuevos": False if solo_activos else is_on("regla_perm_nuevos"),
        "permite_menores": False if solo_activos else is_on("regla_perm_menores"),

        "lider_edad_min": to_int("regla_lider_edad_min"),
        "lider_edad_max": to_int("regla_lider_edad_max"),

        # ── Liderazgo ──
        "permite_liderazgo": is_on("regla_perm_liderazgo", default=True),
        "limite_lideres": to_int("regla_limite_lideres"),

        # ── Estructura ──
        "capacidad_maxima": to_int("regla_capacidad_maxima"),
        "permite_subunidades": is_on("regla_perm_subunidades", default=True),


        # ── Control ──
        "requiere_aprobacion_lider": is_on("regla_req_aprob_lider"),
        "unidad_privada": is_on("regla_unidad_privada"),
    }

    return reglas

# ============================================================
# ROLES
# ============================================================

@login_required
def rol_listado(request):
    roles = RolUnidad.objects.all().order_by("orden", "nombre")
    return render(request, "estructura_app/rol_listado.html", {"roles": roles})


@login_required
def rol_crear(request):
    if request.method == "POST":
        form = RolUnidadForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Rol creado correctamente.")
            return redirect("estructura_app:rol_listado")
    else:
        form = RolUnidadForm()

    return render(request, "estructura_app/rol_form.html", {"form": form, "modo": "crear"})


def _estado_slug(estado):
    if not estado:
        return "vacio"
    s = str(estado).strip().lower()
    s = (s.replace("á", "a").replace("é", "e").replace("í", "i")
           .replace("ó", "o").replace("ú", "u").replace("ñ", "n"))
    return s


# ============================================================
# ASIGNACIÓN (VISTA + AJAX)
# ============================================================

@login_required
def asignacion_unidad(request):
    unidades = Unidad.objects.filter(activa=True).order_by("nombre")
    roles = RolUnidad.objects.filter(activo=True).order_by("orden", "nombre")

    # NO precargamos personas, se cargan por AJAX al guardar contexto
    return render(request, "estructura_app/asignacion_unidad.html", {
        "unidades": unidades,
        "roles": roles,
        "personas": [],
    })

def _get_edad_value(miembro):
    """
    Devuelve la edad como entero si existe.
    Soporta:
    - miembro.edad (si lo guardas como campo o propiedad)
    - miembro.fecha_nacimiento (si existe)
    Si no se puede calcular, devuelve None.
    """
    # 1) Si ya tienes edad calculada/guardada
    if hasattr(miembro, "edad") and miembro.edad is not None:
        try:
            return int(miembro.edad)
        except Exception:
            pass

    # 2) Si tienes fecha_nacimiento (muy común en tu módulo)
    if hasattr(miembro, "fecha_nacimiento") and miembro.fecha_nacimiento:
        from datetime import date
        hoy = date.today()
        fn = miembro.fecha_nacimiento
        edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
        return edad

    return None


def _cumple_rango_edad(miembro, unidad):
    """
    True si el miembro está dentro del rango edad_min/edad_max de la unidad.
    Si la unidad no tiene rango definido, devuelve True.
    Si no se puede calcular edad del miembro, devuelve True (no lo bloqueamos).
    """
    edad_min = getattr(unidad, "edad_min", None)
    edad_max = getattr(unidad, "edad_max", None)

    if edad_min is None and edad_max is None:
        return True

    edad = _get_edad_value(miembro)
    if edad is None:
        return True  # no lo bloqueamos si no podemos medirlo

    if edad_min is not None and edad < edad_min:
        return False
    if edad_max is not None and edad > edad_max:
        return False

    return True

@login_required
def asignacion_unidad_contexto(request):
    unidad_id = (request.GET.get("unidad_id") or "").strip()
    if not unidad_id:
        return JsonResponse({"ok": False, "error": "Falta unidad_id"}, status=400)

    rol_id = (request.GET.get("rol_id") or "").strip()

    unidad = get_object_or_404(Unidad, pk=unidad_id)
    reglas = unidad.reglas or {}

    # -----------------------------------------------------
    # Detectar si el rol seleccionado es de LIDERAZGO
    # -----------------------------------------------------
    rol = None
    rol_es_liderazgo = False
    if rol_id:
        try:
            rol = RolUnidad.objects.get(pk=rol_id)
            rol_es_liderazgo = (getattr(rol, "tipo", None) == RolUnidad.TIPO_LIDERAZGO)
        except RolUnidad.DoesNotExist:
            rol = None
            rol_es_liderazgo = False

    solo_activos = bool(reglas.get("solo_activos", False))

    # =====================================================
    # 1) Membresías actuales (para "miembros" normales)
    # =====================================================
    membresias_actuales = (
        UnidadMembresia.objects
        .filter(unidad=unidad, activo=True)
        .select_related("rol")
    )
    miembros_membresia_ids = set(membresias_actuales.values_list("miembo_fk_id", flat=True))
    rol_membresia_por_miembro = {
        m.miembo_fk_id: (m.rol.nombre if m.rol else "")
        for m in membresias_actuales
    }

    # =====================================================
    # 2) Cargos actuales (para liderazgo)
    # =====================================================
    cargos_actuales = (
        UnidadCargo.objects
        .filter(unidad=unidad, vigente=True)
        .select_related("rol")
    )
    miembros_cargo_ids = set(cargos_actuales.values_list("miembo_fk_id", flat=True))
    rol_cargo_por_miembro = {
        c.miembo_fk_id: (c.rol.nombre if c.rol else "")
        for c in cargos_actuales
    }

    # ✅ Para capacidad y "miembros actuales" de la unidad
    # (esto debe basarse en la membresía, no en los cargos)
    miembros_actuales_count = len(miembros_membresia_ids)

    # =====================================================
    # Query base
    # =====================================================
    # ✅ CRÍTICO: no traer nunca deshabilitados / que ya no están en la iglesia
    qs = Miembro.objects.filter(activo=True)

    # =====================================================
    # REGLA CRÍTICA:
    # - Si unidad es solo_activos -> solo activos (por estado pastoral)
    # - Si rol seleccionado es liderazgo -> solo activos SIEMPRE
    # =====================================================
    if solo_activos or rol_es_liderazgo:
        qs = qs.filter(estado_miembro__iexact="activo")
    else:
        estados_permitidos = ["activo"]

        if reglas.get("permite_observacion"):
            estados_permitidos.append("observacion")
        if reglas.get("permite_pasivos"):
            estados_permitidos.append("pasivo")
        if reglas.get("permite_disciplina"):
            estados_permitidos.append("disciplina")
        if reglas.get("permite_catecumenos"):
            estados_permitidos.append("catecumeno")

        q = Q(estado_miembro__in=estados_permitidos)

        # ✅ Nuevos creyentes SOLO si booleano nuevo_creyente=True
        if reglas.get("permite_nuevos"):
            q |= Q(nuevo_creyente=True)

        # ✅ “Menores / no bautizables” en tu lógica = SIN ESTADO
        # (NO por categoria_edad, porque “adolescente” incluye 12–17 y te ensucia)
        if reglas.get("permite_menores"):
            q |= Q(estado_miembro__isnull=True) | Q(estado_miembro="")

        # Nunca descarriados
        q &= ~Q(estado_miembro__iexact="descarriado")

        qs = qs.filter(q)

    qs = qs.order_by("nombres", "apellidos")

    # =====================================================
    # Construir respuesta
    # =====================================================
    personas = []
 
    for p in qs:

        # ✅ Si es liderazgo: NO aplicar rango edad_min/edad_max de la UNIDAD
        # (para líderes manda el rango lider_edad_min / lider_edad_max)
        if rol_es_liderazgo:
            if not _cumple_rango_edad_liderazgo(p, reglas):
                continue
        else:
            # Miembros normales sí usan el rango de la unidad
            if not _cumple_rango_edad(p, unidad):
                continue

        # ✅ Estado visual (SIN cambiar tus datos)
        # Prioridad:
        # 1) Si tiene estado pastoral -> se muestra tal cual (Activo/Pasivo/etc.)
        # 2) Si no tiene estado:
        #    - si nuevo_creyente=True -> "Nuevo creyente"
        #    - si no -> "No puede ser bautizado" (tu concepto real)
        estado_raw = (p.estado_miembro or "").strip()
        es_nuevo = bool(getattr(p, "nuevo_creyente", False))

        if estado_raw:
            estado_slug = estado_raw.lower()
            estado_label = p.get_estado_miembro_display()
        else:
            if es_nuevo:
                estado_slug = "nuevo"
                estado_label = "Nuevo creyente"
            else:
                # OJO: aquí es el caso "sin estado" pero NO nuevo => no bautizable por edad/regla
                # Para no romper tu UI actual, usamos slug "menor" (ya existe en filtros/CSS)
                estado_slug = "menor"
                estado_label = "No puede ser bautizado"

        # ✅ "Ya en unidad" y "Rol en unidad" según el tipo de rol seleccionado
        if rol_es_liderazgo:
            ya_en_unidad = (p.id in miembros_cargo_ids)
            rol_en_unidad = rol_cargo_por_miembro.get(p.id, "")
        else:
            ya_en_unidad = (p.id in miembros_membresia_ids)
            rol_en_unidad = rol_membresia_por_miembro.get(p.id, "")

        personas.append({
            "id": p.id,
            "nombre": f"{p.nombres} {p.apellidos}",
            "codigo": p.codigo_miembro or "",
            "edad": getattr(p, "edad", None),
            "estado": estado_label,
            "estado_slug": estado_slug,
            "categoria": p.get_categoria_edad_display() if p.categoria_edad else "",
            "ya_en_unidad": ya_en_unidad,
            "rol_en_unidad": rol_en_unidad,
        })

    # =====================================================
    # CAPACIDAD MÁXIMA (SOLO ADVERTENCIA, NO BLOQUEA)
    # =====================================================
    capacidad_maxima = (reglas or {}).get("capacidad_maxima", None)
    capacidad_excedida = False
    capacidad_restante = None
    capacidad_ratio = None

    if capacidad_maxima is not None:
        try:
            capacidad_maxima = int(capacidad_maxima)
            capacidad_restante = capacidad_maxima - miembros_actuales_count
            capacidad_excedida = miembros_actuales_count > capacidad_maxima
            capacidad_ratio = round((miembros_actuales_count / capacidad_maxima) * 100, 2) if capacidad_maxima > 0 else None
        except Exception:
            capacidad_maxima = None

    return JsonResponse({
        "ok": True,
        "unidad": {
            "id": unidad.id,
            "nombre": unidad.nombre,
            "tipo": str(unidad.tipo) if unidad.tipo else "—",
            "miembros_actuales": miembros_actuales_count,

            "capacidad_maxima": capacidad_maxima,
            "capacidad_excedida": capacidad_excedida,
            "capacidad_restante": capacidad_restante,
            "capacidad_ratio": capacidad_ratio,

            "edad_min": unidad.edad_min,
            "edad_max": unidad.edad_max,

            "reglas_aplicadas": {
                "solo_activos": solo_activos,
                "permite_observacion": reglas.get("permite_observacion", False),
                "permite_pasivos": reglas.get("permite_pasivos", False),
                "permite_disciplina": reglas.get("permite_disciplina", False),
                "permite_catecumenos": reglas.get("permite_catecumenos", False),
                "permite_nuevos": reglas.get("permite_nuevos", False),
                "permite_menores": reglas.get("permite_menores", False),
                "permite_liderazgo": reglas.get("permite_liderazgo", True),
                "limite_lideres": reglas.get("limite_lideres", None),
                "rol_es_liderazgo": rol_es_liderazgo,
            }
        },
        "personas": personas,
        "total_elegibles": len(personas),
    })


@login_required
@require_POST
def asignacion_guardar_contexto(request):
    """
    Guarda el contexto unidad+rol (por ahora solo valida y devuelve OK).
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    unidad_id = str(payload.get("unidad_id", "")).strip()
    rol_id = str(payload.get("rol_id", "")).strip()

    if not unidad_id or not rol_id:
        return JsonResponse({"ok": False, "error": "Falta unidad o rol"}, status=400)

    get_object_or_404(Unidad, pk=unidad_id)
    get_object_or_404(RolUnidad, pk=rol_id)

    return JsonResponse({"ok": True})

def _to_int_from_post(post, name, default=None):
    raw = (post.get(name) or "").strip()
    if raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default

@login_required
@require_POST
def asignacion_aplicar(request):
    """
    Recibe: unidad_id, rol_id, miembro_ids[]
    Aplica la asignación según el tipo de rol:
    - LIDERAZGO -> UnidadCargo (vigente=True) + asegura UnidadMembresia activa
    - PARTICIPACIÓN/TRABAJO -> UnidadMembresia (activo=True)

    ✅ Capacidad máxima: SOLO ADVERTENCIA (no bloquea)
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    unidad_id = str(payload.get("unidad_id", "")).strip()
    rol_id = str(payload.get("rol_id", "")).strip()
    miembro_ids = payload.get("miembro_ids") or []

    if not unidad_id or not rol_id:
        return JsonResponse({"ok": False, "error": "Falta unidad o rol"}, status=400)

    if not isinstance(miembro_ids, list) or not miembro_ids:
        return JsonResponse({"ok": False, "error": "No hay miembros seleccionados"}, status=400)

    unidad = get_object_or_404(Unidad, pk=unidad_id)
    rol = get_object_or_404(RolUnidad, pk=rol_id)

    # Sanitizar IDs (solo ints válidos)
    clean_ids = []
    for x in miembro_ids:
        try:
            clean_ids.append(int(x))
        except Exception:
            pass

    if not clean_ids:
        return JsonResponse({"ok": False, "error": "Selección inválida"}, status=400)

    miembros = Miembro.objects.filter(id__in=clean_ids)

    # =====================================================
    # CAPACIDAD MÁXIMA (SOLO ADVERTENCIA, NO BLOQUEA)
    # =====================================================
    reglas = unidad.reglas or {}
    capacidad_maxima = reglas.get("capacidad_maxima", None)

    warning_capacidad = None
    if capacidad_maxima is not None:
        try:
            capacidad_maxima = int(capacidad_maxima)
            actuales = UnidadMembresia.objects.filter(unidad=unidad, activo=True).count()
            proyectado = actuales + len(clean_ids)

            if actuales > capacidad_maxima:
                warning_capacidad = (
                    f"Advertencia: la unidad ya está por encima de su capacidad máxima "
                    f"({actuales}/{capacidad_maxima})."
                )
            elif proyectado > capacidad_maxima:
                warning_capacidad = (
                    f"Advertencia: con esta asignación superarás la capacidad máxima "
                    f"({proyectado}/{capacidad_maxima})."
                )
        except Exception:
            warning_capacidad = None

    tipo = getattr(rol, "tipo", None)

    def _to_int_or_none(v):
        if v is None:
            return None
        try:
            s = str(v).strip()
            if s == "":
                return None
            return int(s)
        except Exception:
            return None

    # =====================================================
    # LIDERAZGO
    # =====================================================
    if tipo == RolUnidad.TIPO_LIDERAZGO:
        permite_liderazgo = bool(reglas.get("permite_liderazgo", False))
        limite_lideres = _to_int_or_none(reglas.get("limite_lideres"))

        # 1) La unidad debe permitir liderazgo
        if not permite_liderazgo:
            return JsonResponse({
                "ok": False,
                "error": "Esta unidad no permite liderazgo. Activa el switch 'Permite liderazgo' en la unidad."
            }, status=400)

        # 2) Regla MÁS importante: liderazgo SOLO para miembros en estado ACTIVO
        no_activos = miembros.exclude(estado_miembro__iexact="activo")
        if no_activos.exists():
            ejemplos = []
            for m in no_activos[:5]:
                est = (m.estado_miembro or "").strip()
                ejemplos.append(f"{m.nombres} {m.apellidos} [{est if est else 'SIN ESTADO'}]")
            extra = f" Ejemplos: {', '.join(ejemplos)}." if ejemplos else ""
            return JsonResponse({
                "ok": False,
                "error": (
                    f"No se puede asignar liderazgo: {no_activos.count()} seleccionado(s) no están en estado ACTIVO."
                    f"{extra}"
                )
            }, status=400)

        # 3) ✅ EDAD DE LIDERAZGO (NO usar edad_min/edad_max de la UNIDAD)
        lider_edad_min = _to_int_or_none(reglas.get("lider_edad_min"))
        lider_edad_max = _to_int_or_none(reglas.get("lider_edad_max"))

        if lider_edad_min is not None or lider_edad_max is not None:
            fuera_rango_lider = []
            for m in miembros:
                edad_val = _get_edad_value(m)
                if edad_val is None:
                    # Si no hay edad, NO bloqueamos por edad (puedes cambiar a bloquear si quieres)
                    continue

                if lider_edad_min is not None and edad_val < lider_edad_min:
                    fuera_rango_lider.append(f"{m.nombres} {m.apellidos} ({edad_val})")
                elif lider_edad_max is not None and edad_val > lider_edad_max:
                    fuera_rango_lider.append(f"{m.nombres} {m.apellidos} ({edad_val})")

            if fuera_rango_lider:
                lm = []
                if lider_edad_min is not None:
                    lm.append(f"mín {lider_edad_min}")
                if lider_edad_max is not None:
                    lm.append(f"máx {lider_edad_max}")
                lm_txt = ", ".join(lm) if lm else "sin rango"

                ejemplos = ", ".join(fuera_rango_lider[:5])
                extra = f" Ejemplos: {ejemplos}." if ejemplos else ""

                return JsonResponse({
                    "ok": False,
                    "error": (
                        "No se puede asignar liderazgo: hay seleccionado(s) fuera del rango de edad "
                        f"permitido para liderazgo ({lm_txt}).{extra}"
                    )
                }, status=400)

        # 4) Límite máximo de líderes (si existe). Vacío => sin límite
        if limite_lideres is not None:
            actuales_lideres = UnidadCargo.objects.filter(
                unidad=unidad,
                vigente=True,
                rol__tipo=RolUnidad.TIPO_LIDERAZGO
            ).count()

            ya_lideres_ids = set(
                UnidadCargo.objects.filter(
                    unidad=unidad,
                    vigente=True,
                    rol__tipo=RolUnidad.TIPO_LIDERAZGO,
                    miembo_fk_id__in=clean_ids
                ).values_list("miembo_fk_id", flat=True)
            )

            nuevos = len([i for i in clean_ids if i not in ya_lideres_ids])
            proyectado = actuales_lideres + nuevos

            if proyectado > limite_lideres:
                return JsonResponse({
                    "ok": False,
                    "error": (
                        f"No se puede asignar: el límite de líderes es {limite_lideres}. "
                        f"Actualmente hay {actuales_lideres} líder(es) vigente(s) y estás intentando añadir {nuevos} nuevo(s)."
                    )
                }, status=400)

        # 5) ASIGNAR / SOBREESCRIBIR liderazgo
        creados = 0
        reactivados = 0
        ya_existian = 0
        hoy = timezone.now().date()

        for m in miembros:
            # Si ya tiene OTRO rol de liderazgo vigente en esta unidad, lo apagamos (sobreescritura)
            otros = UnidadCargo.objects.filter(
                unidad=unidad,
                miembo_fk=m,
                vigente=True,
                rol__tipo=RolUnidad.TIPO_LIDERAZGO
            ).exclude(rol=rol)

            for c in otros:
                c.vigente = False
                if hasattr(c, "fecha_fin"):
                    c.fecha_fin = hoy
                    c.save(update_fields=["vigente", "fecha_fin"])
                else:
                    c.save(update_fields=["vigente"])

            cargo, created_cargo = UnidadCargo.objects.get_or_create(
                unidad=unidad,
                rol=rol,
                miembo_fk=m,
                defaults={
                    "vigente": True,
                    "fecha_inicio": hoy,
                }
            )

            if created_cargo:
                creados += 1
            else:
                if not cargo.vigente:
                    cargo.vigente = True
                    if hasattr(cargo, "fecha_fin"):
                        cargo.fecha_fin = None
                        cargo.save(update_fields=["vigente", "fecha_fin"])
                    else:
                        cargo.save(update_fields=["vigente"])
                    reactivados += 1
                else:
                    ya_existian += 1

            # Asegurar membresía activa (si tu regla lo exige)
            UnidadMembresia.objects.update_or_create(
                unidad=unidad,
                miembo_fk=m,
                defaults={"activo": True, "rol": rol}
            )

        return JsonResponse({
            "ok": True,
            "modo": "liderazgo",
            "creados": creados,
            "reactivados": reactivados,
            "ya_existian": ya_existian,
            "warning": warning_capacidad,
        })

    # =====================================================
    # PARTICIPACIÓN / TRABAJO (MIEMBROS)
    # =====================================================
    # ✅ Aquí sí aplica edad_min/edad_max de la UNIDAD (regla de miembros)
    # (mantengo la lógica que ya tienes; solo agrego el filtro de edad estructural)
    fuera_rango_unidad = []
    for m in miembros:
        if not _cumple_rango_edad(m, unidad):
            edad_val = _get_edad_value(m)
            edad_txt = f"{edad_val}" if edad_val is not None else "—"
            fuera_rango_unidad.append(f"{m.nombres} {m.apellidos} ({edad_txt})")

    if fuera_rango_unidad:
        um = []
        if unidad.edad_min is not None:
            um.append(f"mín {unidad.edad_min}")
        if unidad.edad_max is not None:
            um.append(f"máx {unidad.edad_max}")
        um_txt = ", ".join(um) if um else "sin rango"

        ejemplos = ", ".join(fuera_rango_unidad[:5])
        extra = f" Ejemplos: {ejemplos}." if ejemplos else ""

        return JsonResponse({
            "ok": False,
            "error": (
                "No se puede asignar: hay seleccionado(s) fuera del rango de edad "
                f"de la unidad ({um_txt}).{extra}"
            )
        }, status=400)

    creados = 0
    reactivados = 0
    ya_existian = 0

    for m in miembros:
        obj, created_obj = UnidadMembresia.objects.update_or_create(
            unidad=unidad,
            miembo_fk=m,
            defaults={
                "activo": True,
                "rol": rol,
            }
        )
        if created_obj:
            creados += 1
        else:
            # como es update_or_create, lo consideramos "ya existía"
            ya_existian += 1

    return JsonResponse({
        "ok": True,
        "modo": "membresia",
        "creados": creados,
        "reactivados": reactivados,
        "ya_existian": ya_existian,
        "warning": warning_capacidad,
    })


@login_required
@require_POST
def asignacion_remover(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    unidad_id = str(payload.get("unidad_id", "")).strip()
    rol_id = str(payload.get("rol_id", "")).strip()
    miembro_ids = payload.get("miembro_ids") or []

    if not unidad_id or not rol_id:
        return JsonResponse({"ok": False, "error": "Falta unidad o rol"}, status=400)

    if not isinstance(miembro_ids, list) or not miembro_ids:
        return JsonResponse({"ok": False, "error": "No hay miembros seleccionados"}, status=400)

    unidad = get_object_or_404(Unidad, pk=unidad_id)
    rol = get_object_or_404(RolUnidad, pk=rol_id)

    clean_ids = []
    for x in miembro_ids:
        try:
            clean_ids.append(int(x))
        except Exception:
            pass

    if not clean_ids:
        return JsonResponse({"ok": False, "error": "Selección inválida"}, status=400)

    removidos = 0
    tipo = getattr(rol, "tipo", None)

    # ─────────────────────────────────────────────
    # 🔴 1) LIDERAZGO => desactivar UnidadCargo
    # ─────────────────────────────────────────────
    if tipo == RolUnidad.TIPO_LIDERAZGO:
        cargos = UnidadCargo.objects.filter(
            unidad=unidad,
            miembo_fk_id__in=clean_ids,
            vigente=True,
            rol__tipo=RolUnidad.TIPO_LIDERAZGO,  # importante: por tipo
        )

        for c in cargos:
            c.vigente = False
            if hasattr(c, "fecha_fin"):
                c.fecha_fin = timezone.now().date()
                c.save(update_fields=["vigente", "fecha_fin"])
            else:
                c.save(update_fields=["vigente"])
            removidos += 1

        # ✅ NO tocamos la membresía aquí (solo quitamos liderazgo)
        return JsonResponse({"ok": True, "modo": "liderazgo", "removidos": removidos})

    # ─────────────────────────────────────────────
    # 🟢 2) PARTICIPACIÓN / TRABAJO => desactivar UnidadMembresia
    # ✅ NO filtrar por rol, porque puede ser NULL o distinto
    # ─────────────────────────────────────────────
    membresias = UnidadMembresia.objects.filter(
        unidad=unidad,
        miembo_fk_id__in=clean_ids,
        activo=True
    )

    for m in membresias:
        m.activo = False
        m.save(update_fields=["activo"])
        removidos += 1

    return JsonResponse({"ok": True, "modo": "membresia", "removidos": removidos})


@login_required
@require_POST
def unidad_imagen_actualizar(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)

    if "imagen" in request.FILES:
        unidad.imagen = request.FILES["imagen"]
        unidad.save(update_fields=["imagen", "actualizado_en"])
        messages.success(request, "Imagen actualizada correctamente.")
    else:
        messages.warning(request, "No se seleccionó ninguna imagen.")

    return redirect("estructura_app:unidad_detalle", pk=unidad.pk)

def _to_int_or_none(value):
    if value is None:
        return None
    try:
        s = str(value).strip()
        if s == "":
            return None
        return int(s)
    except Exception:
        return None


def _cumple_rango_edad_liderazgo(miembro, reglas):
    """
    True si el miembro cumple el rango de edad definido para liderazgo en reglas:
      - reglas["lider_edad_min"]
      - reglas["lider_edad_max"]

    Si no hay rango definido, devuelve True (sin límite).
    Si no se puede calcular edad, devuelve True (no bloqueamos).
    """
    edad_min = _to_int_or_none(reglas.get("lider_edad_min"))
    edad_max = _to_int_or_none(reglas.get("lider_edad_max"))

    if edad_min is None and edad_max is None:
        return True

    edad = _get_edad_value(miembro)
    if edad is None:
        return True

    if edad_min is not None and edad < edad_min:
        return False
    if edad_max is not None and edad > edad_max:
        return False

    return True

# ============================================================
# ACTIVIDADES + REPORTES (Actividad y Período)
# ============================================================

MESES = [
    (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
    (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
    (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
]





def _rango_mes(anio: int, mes: int):
    # inicio = 1er día del mes, fin = 1er día del siguiente mes
    inicio = timezone.datetime(anio, mes, 1).date()
    if mes == 12:
        fin = timezone.datetime(anio + 1, 1, 1).date()
    else:
        fin = timezone.datetime(anio, mes + 1, 1).date()
    return inicio, fin


def _generar_resumen_periodo(unidad: Unidad, anio: int, mes: int) -> dict:
    inicio, fin = _rango_mes(anio, mes)

    actividades = (
        ActividadUnidad.objects
        .filter(unidad=unidad, fecha__gte=inicio, fecha__lt=fin)
        .prefetch_related("participantes")
        .order_by("fecha")
    )

    total_actividades = actividades.count()

    # Participantes únicos (en todas las actividades del período)
    participantes_set = set()
    for a in actividades:
        for p in a.participantes.all():
            participantes_set.add(p.pk)

    resumen = {
        "anio": anio,
        "mes": mes,
        "actividades_total": total_actividades,
        "participantes_unicos": len(participantes_set),
    }



    return resumen


@login_required
def unidad_actividades(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)

    actividades = (
        ActividadUnidad.objects
        .filter(unidad=unidad)
        .select_related("responsable")
        .prefetch_related("participantes")
        .order_by("-fecha", "-creado_en")
    )

    return render(request, "estructura_app/unidad_actividades.html", {
        "unidad": unidad,
        "actividades": actividades,
        

    })


@login_required
def actividad_crear(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)

    if request.method == "POST":
        form = ActividadUnidadForm(request.POST, unidad=unidad)
        if form.is_valid():
            act = form.save(commit=False)
            act.unidad = unidad
            act.creado_por = request.user
            act.save()
            form.save_m2m()
            messages.success(request, "Actividad registrada correctamente.")
            return redirect("estructura_app:unidad_actividades", pk=unidad.pk)
        else:
            messages.error(request, "Revisa el formulario: hay campos inválidos.")
    else:
        form = ActividadUnidadForm(unidad=unidad)

    return render(request, "estructura_app/actividad_form.html", {
        "unidad": unidad,
        "form": form,
        
    })


@login_required
def unidad_reportes(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)

    hoy = timezone.localdate()
    anio_sel = int(request.GET.get("anio") or hoy.year)
    mes_sel = int(request.GET.get("mes") or hoy.month)

    reporte, _created = ReporteUnidadPeriodo.objects.get_or_create(
        unidad=unidad,
        anio=anio_sel,
        mes=mes_sel,
        defaults={"creado_por": request.user},
    )

    # Si se pide regenerar o si está vacío, calculamos resumen
    if request.method == "POST" or not (reporte.resumen or {}).get("actividades_total") is not None:
        reporte.resumen = _generar_resumen_periodo(unidad, anio_sel, mes_sel)
        if not reporte.creado_por:
            reporte.creado_por = request.user
        reporte.save()

    form = ReportePeriodoForm(request.POST or None, instance=reporte)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Reporte guardado.")
            return redirect(f"{request.path}?anio={anio_sel}&mes={mes_sel}")

    reportes_lista = (
        ReporteUnidadPeriodo.objects
        .filter(unidad=unidad)
        .order_by("-anio", "-mes")
    )

    return render(request, "estructura_app/unidad_reportes.html", {
        "unidad": unidad,
        "reportes_lista": reportes_lista,
        "reporte": reporte,
        "form": form,
        "anio_sel": anio_sel,
        "mes_sel": mes_sel,
        "MESES": MESES,
        
    })


@login_required
def reporte_unidad_imprimir(request, pk, anio, mes):
    unidad = get_object_or_404(Unidad, pk=pk)
    anio = int(anio)
    mes = int(mes)

    reporte, _ = ReporteUnidadPeriodo.objects.get_or_create(
        unidad=unidad,
        anio=anio,
        mes=mes,
        defaults={"creado_por": request.user},
    )

    if request.GET.get("refresh") == "1" or not reporte.resumen:
        reporte.resumen = _generar_resumen_periodo(unidad, anio, mes)
        reporte.save()

    return render(request, "estructura_app/reportes/reporte_unidad_periodo.html", {
        "unidad": unidad,
        "reporte": reporte,
        "mes_nombre": dict(MESES).get(mes, str(mes)),
    })
