from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.http import HttpResponseForbidden
from datetime import date
from django.db.models import Avg

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

    # Unidades únicas (si tiene varios roles en la misma unidad)
    unidades_map = {}
    for c in cargos:
        if c.unidad_id not in unidades_map:
            unidades_map[c.unidad_id] = c.unidad
    unidades = list(unidades_map.values())

    hoy = date.today()
    anio, mes = hoy.year, hoy.month

    def estado_global_unidad(promedio, porcentaje_riesgo):
        if promedio is None:
            return ("⚪ Sin datos", "sin_datos")

        if porcentaje_riesgo >= 20:
            return ("🔴 En riesgo", "riesgo")

        if promedio >= 4.0:
            return ("🟢 Saludable", "saludable")
        if promedio >= 3.0:
            return ("🟡 En desarrollo", "desarrollo")
        return ("🔴 En riesgo", "riesgo")

    estados_riesgo = ["riesgo", "inactivo", "seguimiento", "observacion", "irregular"]

    unidades_info = []

    for u in unidades:
        evaluacion = EvaluacionUnidad.objects.filter(unidad=u, anio=anio, mes=mes).first()
        total = UnidadMembresia.objects.filter(unidad=u).count()

        qs = EvaluacionMiembro.objects.none()
        if evaluacion:
            qs = EvaluacionMiembro.objects.filter(evaluacion=evaluacion)

        evaluados = qs.count()
        porcentaje = int((evaluados / total) * 100) if total else 0
        promedio = qs.aggregate(avg=Avg("puntaje_general"))["avg"] if evaluacion else None
        en_riesgo = qs.filter(estado__in=estados_riesgo).count() if evaluacion else 0
        lideres = 0

        porcentaje_riesgo = int((en_riesgo / total) * 100) if total else 0
        estado_txt, estado_key = estado_global_unidad(promedio, porcentaje_riesgo)

        if not evaluacion or evaluados == 0:
            accion = "Empezar"
        else:
            estado_workflow = getattr(evaluacion, "estado_workflow", None)
            if estado_workflow and hasattr(EvaluacionUnidad, "ESTADO_CERRADA") and estado_workflow == EvaluacionUnidad.ESTADO_CERRADA:
                accion = "Ver resultados"
            else:
                accion = "Continuar"

        unidades_info.append({
            "unidad": u,
            "evaluacion": evaluacion,
            "total": total,
            "evaluados": evaluados,
            "porcentaje": porcentaje,
            "promedio": promedio,
            "estado_txt": estado_txt,
            "estado_key": estado_key,
            "en_riesgo": en_riesgo,
            "lideres": lideres,
            "accion": accion,
        })

    context = {
        "unidades_info": unidades_info,
        "anio": anio,
        "mes": mes,
    }
    return render(request, "evaluaciones_app/mis_unidades.html", context)


@login_required
@permission_required("evaluaciones_app.add_evaluacionmiembro", raise_exception=True)
@require_http_methods(["GET", "POST"])
@csrf_protect
@transaction.atomic
def evaluar_unidad(request, unidad_id):
    unidad = get_object_or_404(Unidad, id=unidad_id)

    membresias = (
        UnidadMembresia.objects
        .select_related("miembo_fk")
        .filter(unidad=unidad)
    )

    evaluacion, created = EvaluacionUnidad.objects.get_or_create(
        unidad=unidad,
        anio=date.today().year,
        mes=date.today().month,
        defaults={
            "estado_workflow": EvaluacionUnidad.ESTADO_EN_PROGRESO,
            "creado_por": request.user,
        }
    )

    # ✅ Campo correcto: "evaluacion" (no "evaluacion_unidad")
    existentes = {
        ev.miembro.id: ev
        for ev in EvaluacionMiembro.objects.filter(evaluacion=evaluacion)
    }

    if request.method == "POST":
        for mem in membresias:
            if not mem.miembo_fk:
                continue

            m = mem.miembo_fk

            # ✅ Solo los campos que existen en tu modelo
            asistencia = int(request.POST.get(f"asistencia_{m.id}", 3))
            participacion = int(request.POST.get(f"participacion_{m.id}", 3))
            estado = request.POST.get(f"estado_{m.id}", "estable")

            ev = existentes.get(m.id)

            if ev:
                ev.asistencia = asistencia
                ev.participacion = participacion
                ev.estado = estado
                ev.save()
            else:
                # ✅ Campo correcto: "evaluacion" (no "evaluacion_unidad")
                EvaluacionMiembro.objects.create(
                    evaluacion=evaluacion,
                    miembro=m,
                    asistencia=asistencia,
                    participacion=participacion,
                    estado=estado,
                )

        return redirect("evaluaciones_app:evaluar_unidad", unidad_id=unidad.id)

    contexto = {
        "unidad": unidad,
        "membresias": membresias,
        "existentes": existentes,
        "evaluacion": evaluacion,
    }

    return render(request, "evaluaciones_app/evaluar_unidad.html", contexto)