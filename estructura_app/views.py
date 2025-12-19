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
        form = UnidadForm(request.POST)
        if form.is_valid():
            unidad = form.save(commit=False)
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

    if request.method == "POST":
        form = UnidadForm(request.POST, instance=unidad)
        if form.is_valid():
            # Si quieres que también se actualicen reglas al editar, descomenta:
            # unidad = form.save(commit=False)
            # unidad.reglas = _reglas_mvp_from_post(request.POST)
            # unidad.save()
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


@login_required
def unidad_listado(request):
    query = request.GET.get("q", "").strip()

    unidades = Unidad.objects.all().order_by("nombre")
    if query:
        unidades = unidades.filter(Q(nombre__icontains=query) | Q(codigo__icontains=query))

    return render(request, "estructura_app/unidad_listado.html", {
        "unidades": unidades,
        "query": query,
    })


@login_required
def unidad_detalle(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)
    return render(request, "estructura_app/unidad_detalle.html", {"unidad": unidad})


def _reglas_mvp_from_post(post):
    """
    Lee reglas MVP desde request.POST y devuelve un dict listo para guardar en JSONField.
    'solo_activos' por defecto: True.
    Si 'solo_activos' está activo, BLOQUEA (fuerza False) las demás reglas de membresía.
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

    permite_menores = False if solo_activos else is_on("regla_perm_menores", default=False)
    permite_observacion = False if solo_activos else is_on("regla_perm_observacion", default=False)
    permite_nuevos = False if solo_activos else is_on("regla_perm_nuevos", default=False)
    permite_catecumenos = False if solo_activos else is_on("regla_perm_catecumenos", default=False)
    permite_visitantes = False if solo_activos else is_on("regla_perm_visitantes", default=False)

    return {
        "solo_activos": solo_activos,
        "permite_menores": permite_menores,
        "permite_observacion": permite_observacion,
        "permite_nuevos": permite_nuevos,
        "permite_catecumenos": permite_catecumenos,
        "permite_visitantes": permite_visitantes,

        "capacidad_maxima": to_int("regla_capacidad_maxima", default=None),
        "permite_subunidades": is_on("regla_perm_subunidades", default=True),

        "requiere_aprobacion_lider": is_on("regla_req_aprob_lider", default=False),
        "unidad_privada": is_on("regla_unidad_privada", default=False),
    }


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

@login_required
def asignacion_unidad_contexto(request):
    unidad_id = (request.GET.get("unidad_id") or "").strip()
    if not unidad_id:
        return JsonResponse({"ok": False, "error": "Falta unidad_id"}, status=400)

    unidad = get_object_or_404(Unidad, pk=unidad_id)
    reglas = unidad.reglas or {}

    solo_activos = bool(reglas.get("solo_activos", True))

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

        # OJO: visitantes SOLO si de verdad existe ese estado en tu modelo
        if reglas.get("permite_visitantes"):
            estados_permitidos.append("visitante")

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
        personas.append({
            "id": p.id,
            "nombre": f"{p.nombres} {p.apellidos}",
            "codigo": p.codigo_miembro or "",
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
            "reglas_aplicadas": {
                "solo_activos": solo_activos,
                "permite_observacion": reglas.get("permite_observacion", False),
                "permite_pasivos": reglas.get("permite_pasivos", False),
                "permite_disciplina": reglas.get("permite_disciplina", False),
                "permite_catecumenos": reglas.get("permite_catecumenos", False),
                "permite_nuevos": reglas.get("permite_nuevos", False),
                "permite_visitantes": reglas.get("permite_visitantes", False),
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

