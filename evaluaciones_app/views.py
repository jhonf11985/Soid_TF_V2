from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.http import HttpResponseForbidden
from datetime import date
from django.db.models import Avg,Count
from miembros_app.models import Miembro
from .forms import EvaluacionPerfilUnidadForm

from .models import EvaluacionUnidad, EvaluacionMiembro
from estructura_app.models import Unidad, UnidadCargo, UnidadMembresia


def _get_miembro_from_user(user):
    """
    Devuelve el Miembro vinculado al User.
    """
    # 1) VÍNCULO REAL EN TU MODELO: Miembro.usuario
    try:
        from miembros_app.models import Miembro
        m = Miembro.objects.filter(usuario=user).first()
        if m:
            return m
    except Exception:
        pass

    # 2) user.miembro (si en algún momento existiera)
    m = getattr(user, "miembro", None)
    if m:
        return m

    # 3) otros nombres posibles (fallback)
    for attr in ("miembro_fk", "miembro_vinculado", "miembro_asociado"):
        m = getattr(user, attr, None)
        if m:
            return m

    # 4) user.perfil.miembro (si usas perfiles)
    perfil = getattr(user, "perfil", None)
    if perfil:
        m = getattr(perfil, "miembro", None)
        if m:
            return m

    return None


def _user_es_lider_de_unidad(user, unidad_id):
    miembro = _get_miembro_from_user(user)
    if not miembro:
        return False
    return UnidadCargo.objects.filter(
        unidad_id=unidad_id,
        miembo_fk=miembro,
        vigente=True,
    ).exists()

@login_required
def mis_unidades(request):
    miembro = _get_miembro_from_user(request.user)
    if not miembro:
        return HttpResponseForbidden(
            "Este usuario no tiene un miembro vinculado. Vincula el usuario a un miembro para poder evaluar unidades."
        )

    cargos = (
        UnidadCargo.objects
        .select_related("unidad", "rol")
        .filter(miembo_fk=miembro, vigente=True)
        .order_by("unidad__nombre")
    )

    unidades_map = {}
    for c in cargos:
        if c.unidad_id not in unidades_map:
            unidades_map[c.unidad_id] = c.unidad
    unidades = list(unidades_map.values())

    hoy = date.today()
    anio, mes = hoy.year, hoy.month

    unidades_info = []

    for u in unidades:
        perfil, _ = EvaluacionPerfilUnidad.objects.get_or_create(unidad=u)

        evaluacion, _ = EvaluacionUnidad.objects.get_or_create(
            unidad=u,
            anio=anio,
            mes=mes,
            defaults={"perfil": perfil, "creado_por": request.user},
        )

        membresias_qs = UnidadMembresia.objects.filter(unidad=u)
        if perfil.excluir_evaluador:
            membresias_qs = membresias_qs.exclude(miembo_fk=miembro)

        total = membresias_qs.count()

        qs = EvaluacionMiembro.objects.none()
        if evaluacion:
            qs = EvaluacionMiembro.objects.filter(evaluacion=evaluacion)

        # ✅ SOLO cuentan como evaluados los que ya fueron guardados (tienen evaluado_por)
        evaluados = qs.filter(evaluado_por__isnull=False).count()
        pendientes = max(total - evaluados, 0)
        porcentaje = int((evaluados / total) * 100) if total else 0

        # ✅ estado + acción según progreso (no según promedio)
        if not evaluacion:
            estado_txt = "📝 Sin evaluación creada"
            accion = "Empezar"
        elif evaluados == 0:
            estado_txt = "🟡 Sin iniciar"
            accion = "Empezar"
        elif evaluados < total:
            estado_txt = "🟠 En progreso"
            accion = "Continuar"
        else:
            estado_txt = "🟢 Completada"
            accion = "Completado"


        unidades_info.append({
            "unidad": u,
            "perfil": perfil,
            "evaluacion": evaluacion,
            "total": total,
            "evaluados": evaluados,
            "pendientes": pendientes,
            "porcentaje": porcentaje,
          
            "estado_txt": estado_txt,
            "accion": accion,
        })

    context = {
        "unidades_info": unidades_info,
        "anio": anio,
        "mes": mes,
    }
    return render(request, "evaluaciones_app/mis_unidades.html", context)


from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from estructura_app.models import Unidad, UnidadMembresia
from .models import EvaluacionUnidad, EvaluacionMiembro, EvaluacionPerfilUnidad

# usa tu helper existente _get_miembro_from_user y _user_es_lider_de_unidad

@login_required
@permission_required("evaluaciones_app.add_evaluacionmiembro", raise_exception=True)
@require_http_methods(["GET", "POST"])
@csrf_protect
@transaction.atomic
def evaluar_unidad(request, unidad_id):
    unidad = get_object_or_404(Unidad, id=unidad_id)

    # ✅ Buscar o crear perfil de evaluación (UNA sola vez)
    perfil, perfil_creado = EvaluacionPerfilUnidad.objects.get_or_create(unidad=unidad)

    # ✅ Si se acaba de crear, seguro es perfil por defecto
    perfil_es_default = perfil_creado

    # Buscar o crear evaluación del mes actual
    hoy = timezone.now()
    evaluacion, _ = EvaluacionUnidad.objects.get_or_create(
        unidad=unidad,
        anio=hoy.year,
        mes=hoy.month,
        defaults={"perfil": perfil, "creado_por": request.user},
    )

    miembros = Miembro.objects.filter(
        membresias_unidad__unidad=unidad,
        estado_miembro="activo",
    ).distinct()

    # Crear registros si no existen
    for m in miembros:
        EvaluacionMiembro.objects.get_or_create(
            evaluacion=evaluacion,
            miembro=m,
        )

    if request.method == "POST":
        for m in miembros:
            item = EvaluacionMiembro.objects.get(
                evaluacion=evaluacion,
                miembro=m,
            )

            # ===== BLOQUE ORGANIZACIONAL =====
            item.asistencia = int(request.POST.get(f"asistencia_{m.id}", 3))
            item.participacion = int(request.POST.get(f"participacion_{m.id}", 3))
            item.compromiso = int(request.POST.get(f"compromiso_{m.id}", 3))
            item.actitud = int(request.POST.get(f"actitud_{m.id}", 3))
            item.integracion = int(request.POST.get(f"integracion_{m.id}", 3))

            # ===== BLOQUE ESPIRITUAL =====
            item.madurez_espiritual = int(request.POST.get(f"madurez_espiritual_{m.id}", 3))
            item.estado_espiritual = request.POST.get(
                f"estado_espiritual_{m.id}",
                EvaluacionMiembro.ESTADO_ESTABLE,
            )

            # Observación
            item.observacion = request.POST.get(f"observacion_{m.id}", "")

            item.evaluado_por = request.user
            item.recalcular_puntaje_general()

            item.save()

        messages.success(request, "✅ Evaluación guardada correctamente.")
        return redirect("evaluaciones_app:evaluar_unidad", unidad_id=unidad.id)
    items = EvaluacionMiembro.objects.filter(evaluacion=evaluacion).select_related("miembro")

    contexto = {
        "unidad": unidad,
        "evaluacion": evaluacion,
        "items": items,
        "perfil": perfil,
        "perfil_es_default": perfil_es_default,
    }

    return render(request, "evaluaciones_app/evaluar_unidad.html", contexto)



@login_required
def perfil_evaluacion_unidad(request, unidad_id):
    unidad = get_object_or_404(Unidad, id=unidad_id)

        # Ejemplo: validar que el usuario sea líder de la unidad
    miembro = getattr(request.user, "miembro", None)
    if not miembro:
        return HttpResponseForbidden("No tienes permiso para configurar esta unidad.")

    perfil, _ = EvaluacionPerfilUnidad.objects.get_or_create(unidad=unidad)

    if request.method == "POST":
        form = EvaluacionPerfilUnidadForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Perfil de evaluación actualizado.")
            return redirect("evaluaciones_app:perfil_evaluacion_unidad", unidad_id=unidad.id)
    else:
        form = EvaluacionPerfilUnidadForm(instance=perfil)

    return render(request, "evaluaciones_app/perfil_evaluacion_unidad.html", {
        "unidad": unidad,
        "perfil": perfil,
        "form": form,
    })




@login_required
def ver_resultados_unidad(request, evaluacion_id):
    evaluacion = get_object_or_404(
        EvaluacionUnidad.objects.select_related("unidad", "perfil"),
        id=evaluacion_id
    )

    items = (
        EvaluacionMiembro.objects
        .filter(evaluacion=evaluacion)
        .select_related("miembro")
        .order_by("miembro__nombres", "miembro__apellidos")
    )

    total = items.count()
    evaluados = items.exclude(puntaje_general__isnull=True).count()
    pendientes = total - evaluados

    # Promedios (solo si hay registros)
    promedios = items.aggregate(
        avg_asistencia=Avg("asistencia"),
        avg_participacion=Avg("participacion"),
        avg_compromiso=Avg("compromiso"),
        avg_actitud=Avg("actitud"),
        avg_integracion=Avg("integracion"),
        avg_madurez=Avg("madurez_espiritual"),
        avg_puntaje=Avg("puntaje_general"),
    )

    # Distribución de puntaje 1–5
    dist = (
        items.values("puntaje_general")
        .annotate(c=Count("id"))
        .order_by("puntaje_general")
    )
    dist_map = {d["puntaje_general"]: d["c"] for d in dist}
    distribucion = {
        5: dist_map.get(5, 0),
        4: dist_map.get(4, 0),
        3: dist_map.get(3, 0),
        2: dist_map.get(2, 0),
        1: dist_map.get(1, 0),
    }
    avg_puntaje = promedios.get("avg_puntaje") or 0

    if avg_puntaje >= 4.2:
        semaforo = ("🟢", "Fuerte", "La unidad está sólida y estable.")
    elif avg_puntaje >= 3.6:
        semaforo = ("🔵", "Bien", "La unidad va bien, con detalles a fortalecer.")
    elif avg_puntaje >= 3.0:
        semaforo = ("🟡", "En proceso", "La unidad necesita ajustes para mejorar consistencia.")
    elif avg_puntaje >= 2.5:
        semaforo = ("🟠", "Débil", "Hay señales de debilidad. Requiere seguimiento cercano.")
    else:
        semaforo = ("🔴", "Crítica", "Se recomienda intervención y plan inmediato.")

    dim_proms = [
        ("Asistencia", promedios.get("avg_asistencia")),
        ("Participación", promedios.get("avg_participacion")),
        ("Compromiso", promedios.get("avg_compromiso")),
        ("Actitud", promedios.get("avg_actitud")),
        ("Integración", promedios.get("avg_integracion")),
        ("Madurez", promedios.get("avg_madurez")),
    ]

    # Filtrar None y ordenar
    dim_proms = [(n, v) for n, v in dim_proms if v is not None]
    dim_proms_sorted = sorted(dim_proms, key=lambda x: x[1], reverse=True)

    fortalezas = dim_proms_sorted[:2]
    oportunidades = sorted(dim_proms, key=lambda x: x[1])[:2]

    context = {
        "evaluacion": evaluacion,
        "unidad": evaluacion.unidad,
        "perfil": evaluacion.perfil,
        "items": items,
        "total": total,
        "evaluados": evaluados,
        "pendientes": pendientes,
        "promedios": promedios,
        "distribucion": distribucion,
           "semaforo": semaforo,
   "fortalezas": fortalezas,
   "oportunidades": oportunidades,
    }
    return render(request, "evaluaciones_app/resultados_unidad.html", context)
