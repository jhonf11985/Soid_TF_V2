import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from miembros_app.models import Miembro
from .forms import UnidadForm, RolUnidadForm
from .models import Unidad, TipoUnidad, RolUnidad, UnidadMembresia, UnidadCargo


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
        .select_related("miembo_fk")
        .order_by("miembo_fk__nombres", "miembo_fk__apellidos")
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

    categorias_edad = [{"nombre": k, "cantidad": v} for k, v in cat_map.items()]

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

    return render(request, "estructura_app/unidad_detalle.html", {
        "unidad": unidad,
        "miembros_asignados": miembros_asignados,
        "lideres_asignados": lideres_asignados,
        "resumen": resumen,
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

    unidad = get_object_or_404(Unidad, pk=unidad_id)
    reglas = unidad.reglas or {}

    solo_activos = bool(reglas.get("solo_activos", False))

    miembros_actuales_ids = set(
        UnidadMembresia.objects.filter(unidad=unidad, activo=True)
        .values_list("miembo_fk_id", flat=True)
    )

    # ✅ IMPORTANTE: no filtramos por Miembro.activo=True
    # porque tu participación depende del ESTADO (estado_miembro)
    qs = Miembro.objects.all()

    # =====================================================
    # APLICAR REGLAS DE MEMBRESÍA (POR ESTADO)
    # =====================================================
    if solo_activos:
        qs = qs.filter(estado_miembro="activo")
    else:
        # ✅ activos SIEMPRE incluidos
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

        # Nuevos creyentes (si lo usas como extra aparte del estado)
        if reglas.get("permite_nuevos"):
            q |= Q(nuevo_creyente=True)

        # Menores: tú dijiste que "estado vacío" representa menores
        # tu código actual usa categoria_edad; lo dejamos, pero añadimos estado vacío también
        if reglas.get("permite_menores"):
            q |= Q(estado_miembro__isnull=True) | Q(estado_miembro="")
            q |= Q(categoria_edad__in=["infante", "nino", "adolescente"])

        # Nunca descarriados (si ese estado existe)
        q &= ~Q(estado_miembro="descarriado")

        qs = qs.filter(q)

    qs = qs.order_by("nombres", "apellidos")

    personas = []
    for p in qs:
        # ✅ FILTRO #1: rango de edad (antes de devolverlo a la lista)
        if not _cumple_rango_edad(p, unidad):
            continue

        personas.append({
            "id": p.id,
            "nombre": f"{p.nombres} {p.apellidos}",
            "codigo": p.codigo_miembro or "",
            "edad": p.edad,
            "estado": p.get_estado_miembro_display() if p.estado_miembro else "",
            "estado_slug": p.estado_miembro or "vacio",
            "categoria": p.get_categoria_edad_display() if p.categoria_edad else "",
            "ya_en_unidad": p.id in miembros_actuales_ids,
        })


    return JsonResponse({
        "ok": True,
        "unidad": {
            "id": unidad.id,
            "nombre": unidad.nombre,
            "tipo": str(unidad.tipo) if unidad.tipo else "—",
            "miembros_actuales": len(miembros_actuales_ids),
                    
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

    creados = 0
    reactivados = 0
    ya_existian = 0

    # Para no reventar si viene algo raro
    tipo = getattr(rol, "tipo", None)

    # ------------------------------------------------------------
    # 1) ROLES DE LIDERAZGO => UnidadCargo + asegurar membresía
    # ------------------------------------------------------------
    if tipo == RolUnidad.TIPO_LIDERAZGO:
        for m in miembros:
            # A) Crear/activar membresía si no existe (regla tuya)
            memb, created_memb = UnidadMembresia.objects.get_or_create(
                unidad=unidad,
                miembo_fk=m,
                defaults={"activo": True}
            )
            if not created_memb and not memb.activo:
                memb.activo = True
                memb.save(update_fields=["activo"])
                reactivados += 1

            # B) Cargo vigente para (unidad, rol, miembro)
            cargo, created_cargo = UnidadCargo.objects.get_or_create(
                unidad=unidad,
                rol=rol,
                miembro=m,  # AJUSTA este nombre de FK si en tu modelo se llama distinto
                defaults={
                    "vigente": True,
                    "fecha_inicio": timezone.now().date() if hasattr(timezone.now(), "date") else timezone.now()
                }
            )

            if created_cargo:
                creados += 1
            else:
                if not cargo.vigente:
                    cargo.vigente = True
                    # si tienes fecha_fin, límpiala
                    if hasattr(cargo, "fecha_fin"):
                        cargo.fecha_fin = None
                    cargo.save()
                    reactivados += 1
                else:
                    ya_existian += 1

        return JsonResponse({
            "ok": True,
            "modo": "liderazgo",
            "creados": creados,
            "reactivados": reactivados,
            "ya_existian": ya_existian,
        })

    # ------------------------------------------------------------
    # 2) PARTICIPACIÓN / TRABAJO => UnidadMembresia
    # ------------------------------------------------------------
    for m in miembros:
        memb, created_memb = UnidadMembresia.objects.get_or_create(
            unidad=unidad,
            miembo_fk=m,
            defaults={"activo": True}
        )

        if created_memb:
            creados += 1
        else:
            if not memb.activo:
                memb.activo = True
                memb.save(update_fields=["activo"])
                reactivados += 1
            else:
                ya_existian += 1

        # (Opcional) Si quieres guardar el rol también en membresía y tu modelo lo tiene:
        # if hasattr(memb, "rol") and memb.rol_id != rol.id:
        #     memb.rol = rol
        #     memb.save(update_fields=["rol"])

    return JsonResponse({
        "ok": True,
        "modo": "membresia",
        "creados": creados,
        "reactivados": reactivados,
        "ya_existian": ya_existian,
    })



@login_required
@require_POST
def asignacion_remover(request):
    """
    Recibe: unidad_id, rol_id (opcional), miembro_ids[]
    - Si rol es LIDERAZGO: quita el cargo (vigente=False) para ese rol y unidad.
    - Si rol NO es liderazgo o no viene rol: quita membresía (activo=False) en esa unidad.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    unidad_id = str(payload.get("unidad_id", "")).strip()
    rol_id = str(payload.get("rol_id", "")).strip()
    miembro_ids = payload.get("miembro_ids") or []

    if not unidad_id:
        return JsonResponse({"ok": False, "error": "Falta unidad"}, status=400)

    if not isinstance(miembro_ids, list) or not miembro_ids:
        return JsonResponse({"ok": False, "error": "No hay miembros seleccionados"}, status=400)

    unidad = get_object_or_404(Unidad, pk=unidad_id)

    clean_ids = []
    for x in miembro_ids:
        try:
            clean_ids.append(int(x))
        except Exception:
            pass

    if not clean_ids:
        return JsonResponse({"ok": False, "error": "Selección inválida"}, status=400)

    # Si viene rol, lo validamos
    rol = None
    if rol_id:
        rol = get_object_or_404(RolUnidad, pk=rol_id)

    removidos = 0

    # 1) Si es liderazgo => desactivar cargo (vigente=False)
    if rol and rol.tipo == RolUnidad.TIPO_LIDERAZGO:
        qs = UnidadCargo.objects.filter(
            unidad=unidad,
            rol=rol,
            miembo_fk_id__in=clean_ids,
            vigente=True
        )
        removidos = qs.update(vigente=False)
        return JsonResponse({"ok": True, "modo": "liderazgo", "removidos": removidos})

    # 2) Si NO liderazgo => desactivar membresía (activo=False)
    qs = UnidadMembresia.objects.filter(
        unidad=unidad,
        miembo_fk_id__in=clean_ids,
        activo=True
    )
    removidos = qs.update(activo=False)

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
