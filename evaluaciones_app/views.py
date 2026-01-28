from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.http import HttpResponseForbidden
from datetime import date
from django.db.models import Avg
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

        evaluacion = EvaluacionUnidad.objects.filter(unidad=u, anio=anio, mes=mes).first()

        membresias_qs = UnidadMembresia.objects.filter(unidad=u)
        if perfil.excluir_evaluador:
            membresias_qs = membresias_qs.exclude(miembo_fk=miembro)

        total = membresias_qs.count()

        qs = EvaluacionMiembro.objects.none()
        if evaluacion:
            qs = EvaluacionMiembro.objects.filter(evaluacion=evaluacion)

        evaluados = qs.count()
        pendientes = max(total - evaluados, 0)
        porcentaje = int((evaluados / total) * 100) if total else 0

        promedio = qs.aggregate(avg=Avg("puntaje_general"))["avg"] if evaluacion else None

        # Semáforo simple basado en promedio (puedes cambiar reglas luego)
        if promedio is None:
            estado_txt = "⚪ Sin datos"
        elif promedio >= 4:
            estado_txt = "🟢 Saludable"
        elif promedio >= 3:
            estado_txt = "🟡 En desarrollo"
        else:
            estado_txt = "🔴 En riesgo"

        accion = "Empezar" if evaluados == 0 else "Continuar"

        unidades_info.append({
            "unidad": u,
            "perfil": perfil,
            "evaluacion": evaluacion,
            "total": total,
            "evaluados": evaluados,
            "pendientes": pendientes,
            "porcentaje": porcentaje,
            "promedio": promedio,
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

    # Buscar o crear perfil de evaluación
    perfil, _ = EvaluacionPerfilUnidad.objects.get_or_create(unidad=unidad)

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
            item.save()

        messages.success(request, "✅ Evaluación guardada correctamente.")
        return redirect("evaluaciones_app:evaluar_unidad", unidad_id=unidad.id)

    items = EvaluacionMiembro.objects.filter(evaluacion=evaluacion).select_related("miembro")

    contexto = {
        "unidad": unidad,
        "evaluacion": evaluacion,
        "items": items,
        "perfil": perfil,
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