from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from estructura_app.models import Unidad, UnidadCargo, UnidadMembresia
from .models import EvaluacionUnidad, EvaluacionMiembro


def _get_miembro_from_user(user):
    """
    Devuelve el Miembro vinculado al User.

    En tu sistema, el vínculo real es: Miembro.usuario (FK/OneToOne hacia User).
    """
    # ✅ 1) VÍNCULO REAL EN TU MODELO: Miembro.usuario
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

    # DEBUG - quitar después
    print("DEBUG user:", request.user, "| ID:", request.user.id)
    from miembros_app.models import Miembro
    test = Miembro.objects.filter(usuario_id=request.user.id).first()
    print("DEBUG miembro:", test)
    # FIN DEBUG
    



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

    # Sacamos unidades únicas (si tiene varios roles en la misma unidad)
    unidades_map = {}
    for c in cargos:
        if c.unidad_id not in unidades_map:
            unidades_map[c.unidad_id] = c.unidad
    unidades = list(unidades_map.values())

    context = {
        "unidades": unidades,
    }
    return render(request, "evaluaciones_app/mis_unidades.html", context)


@login_required
def evaluar_unidad(request, unidad_id):
    miembro = _get_miembro_from_user(request.user)
    if not miembro:
        return HttpResponseForbidden(
            "Este usuario no tiene un miembro vinculado. Vincula el usuario a un miembro para poder evaluar."
        )

    # Seguridad: solo líderes de esa unidad
    if not _user_es_lider_de_unidad(request.user, unidad_id):
        return HttpResponseForbidden("No tienes permisos para evaluar esta unidad.")

    unidad = get_object_or_404(Unidad, pk=unidad_id)

    hoy = timezone.localdate()
    anio = hoy.year
    mes = hoy.month

    evaluacion_unidad, _created = EvaluacionUnidad.objects.get_or_create(
        unidad=unidad,
        anio=anio,
        mes=mes,
        defaults={
            "estado": EvaluacionUnidad.ESTADO_EN_PROGRESO,
            "creado_por": request.user,
        }
    )

    # Miembros activos de la unidad
    membresias = (
        UnidadMembresia.objects
        .select_related("miembo_fk", "rol")
        .filter(unidad=unidad, activo=True)
        .order_by("miembo_fk__nombres", "miembo_fk__apellidos")
    )

    # Cargar evaluaciones existentes para este periodo (para editar sin perder)
    existentes = {
        em.miembro_id: em
        for em in EvaluacionMiembro.objects.filter(evaluacion=evaluacion_unidad)
    }

    if request.method == "POST":
        # Guardado masivo
        with transaction.atomic():
            guardados = 0
            for memb in membresias:
                mid = memb.miembo_fk_id
                a = request.POST.get(f"asistencia_{mid}", "")
                p = request.POST.get(f"participacion_{mid}", "")
                e = request.POST.get(f"estado_{mid}", "")
                obs = (request.POST.get(f"observacion_{mid}", "") or "").strip()

                # Si el líder no tocó nada, lo saltamos (para que sea rápido)
                if not (a or p or e or obs):
                    continue

                # Defaults seguros si faltan
                asistencia = int(a) if a else 3
                participacion = int(p) if p else 3
                estado = e if e else EvaluacionMiembro.ESTADO_NORMAL

                EvaluacionMiembro.objects.update_or_create(
                    evaluacion=evaluacion_unidad,
                    miembro_id=mid,
                    defaults={
                        "asistencia": asistencia,
                        "participacion": participacion,
                        "estado": estado,
                        "observacion": obs[:255],
                        "evaluado_por": request.user,
                    }
                )
                guardados += 1

        messages.success(request, f"Evaluación guardada. Registros actualizados: {guardados}.")
        return redirect("evaluaciones_app:evaluar_unidad", unidad_id=unidad_id)

    context = {
        "unidad": unidad,
        "evaluacion_unidad": evaluacion_unidad,
        "membresias": membresias,
        "existentes": existentes,
    }
    return render(request, "evaluaciones_app/evaluar_unidad.html", context)
