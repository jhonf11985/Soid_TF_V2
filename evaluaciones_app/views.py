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
import json
from django.http import JsonResponse
from .models import EvaluacionUnidad, EvaluacionMiembro, EvaluacionPerfilUnidad
from estructura_app.models import Unidad, UnidadCargo, UnidadMembresia
from django.views.decorators.http import require_POST

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

        # ✅ Lógica según modo
        if perfil.es_libre:
            # Modo LIBRE: buscar la evaluación activa más reciente (no cerrada)
            evaluacion = EvaluacionUnidad.objects.filter(
                unidad=u,
                anio=anio,
                mes=mes,
                estado_workflow__in=[
                    EvaluacionUnidad.ESTADO_BORRADOR,
                    EvaluacionUnidad.ESTADO_EN_PROGRESO
                ]
            ).order_by('-numero_secuencia').first()

            # Contar evaluaciones cerradas del período
            evaluaciones_cerradas = EvaluacionUnidad.objects.filter(
                unidad=u,
                anio=anio,
                mes=mes,
                estado_workflow=EvaluacionUnidad.ESTADO_CERRADA
            ).count()
        else:
            # Modo AUTO: una sola evaluación por período
            evaluacion, _ = EvaluacionUnidad.objects.get_or_create(
                unidad=u,
                anio=anio,
                mes=mes,
                numero_secuencia=1,
                defaults={"perfil": perfil, "creado_por": request.user},
            )
            evaluaciones_cerradas = 0

        # ✅ Contar evaluaciones cerradas (para historial)
        total_cerradas = EvaluacionUnidad.objects.filter(
            unidad=u,
            estado_workflow=EvaluacionUnidad.ESTADO_CERRADA
        ).count()

        membresias_qs = UnidadMembresia.objects.filter(unidad=u)
        if perfil.excluir_evaluador:
            membresias_qs = membresias_qs.exclude(miembo_fk=miembro)

        total = membresias_qs.count()

        qs = EvaluacionMiembro.objects.none()
        if evaluacion:
            qs = EvaluacionMiembro.objects.filter(evaluacion=evaluacion)



        # ✅ SOLO cuentan como evaluados los que ya fueron guardados (tienen evaluado_por)
        evaluados = qs.filter(evaluado_por__isnull=False).count()
        # ✅ detectar si hay evaluación en proceso
        hay_progreso = evaluados > 0 or (evaluacion and evaluacion.estado_workflow == EvaluacionUnidad.ESTADO_EN_PROGRESO)

        pendientes = max(total - evaluados, 0)
        porcentaje = int((evaluados / total) * 100) if total else 0

        
        # ✅ Estado (workflow manda)
        if not evaluacion:
            estado_txt = "🔒 Sin evaluación creada"
        elif evaluacion.estado_workflow == EvaluacionUnidad.ESTADO_CERRADA:
            estado_txt = "🟢 Completada"
        elif evaluados == 0:
            estado_txt = "🟡 Sin iniciar"
        else:
            # incluye el caso 100% pero reabierta (EN_PROGRESO)
            estado_txt = "🟠 En progreso"

        # ✅ Acción (considera workflow + progreso)
        if not evaluacion or evaluados == 0:
            accion = "Empezar"
        elif evaluacion.estado_workflow == EvaluacionUnidad.ESTADO_CERRADA:
            # Solo mostrar "Completado" si realmente está cerrada
            accion = "Completado"
        elif evaluados < total:
            accion = "Continuar"
        else:
            # 100% evaluados pero EN_PROGRESO (fue reabierta) → permitir continuar/editar
            accion = "Continuar"

        # ✅ Detectar si fue reabierta (100% pero no cerrada)
        reabierta = (
            evaluacion and 
            evaluacion.estado_workflow == EvaluacionUnidad.ESTADO_EN_PROGRESO and 
            evaluados == total and 
            total > 0
        )

        unidades_info.append({
            "unidad": u,
            "perfil": perfil,
            "evaluacion": evaluacion,
            "total": total,
            "evaluados": evaluados,
            "pendientes": pendientes,
            "porcentaje": porcentaje,
            "bloquear_configuracion": hay_progreso,
            "reabierta": reabierta,
            "estado_txt": estado_txt,
            "accion": accion,
            "es_modo_libre": perfil.es_libre,
            "evaluaciones_cerradas": total_cerradas,
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
def evaluar_unidad(request, unidad_id, evaluacion_id=None):
    unidad = get_object_or_404(Unidad, id=unidad_id)

    # ✅ Buscar o crear perfil de evaluación (UNA sola vez)
    perfil, perfil_creado = EvaluacionPerfilUnidad.objects.get_or_create(unidad=unidad)

    # ✅ Si se acaba de crear, seguro es perfil por defecto
    perfil_es_default = perfil_creado

    hoy = timezone.now()

    # ✅ Si viene evaluacion_id, cargar esa evaluación específica
    if evaluacion_id:
        evaluacion = get_object_or_404(EvaluacionUnidad, id=evaluacion_id, unidad=unidad)
    elif perfil.es_libre:
        # Modo LIBRE: buscar evaluación activa (no cerrada) o crear nueva
        evaluacion = EvaluacionUnidad.objects.filter(
            unidad=unidad,
            anio=hoy.year,
            mes=hoy.month,
            estado_workflow__in=[
                EvaluacionUnidad.ESTADO_BORRADOR,
                EvaluacionUnidad.ESTADO_EN_PROGRESO
            ]
        ).order_by('-numero_secuencia').first()

        if not evaluacion:
            # Crear nueva evaluación (el save() auto-calcula numero_secuencia)
            evaluacion = EvaluacionUnidad.objects.create(
                unidad=unidad,
                anio=hoy.year,
                mes=hoy.month,
                perfil=perfil,
                creado_por=request.user,
            )
    else:
        # Modo AUTO: una sola evaluación por período
        evaluacion, _ = EvaluacionUnidad.objects.get_or_create(
            unidad=unidad,
            anio=hoy.year,
            mes=hoy.month,
            numero_secuencia=1,
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

            # Observación
            item.observacion = request.POST.get(f"observacion_{m.id}", "")

            item.evaluado_por = request.user
            item.recalcular_puntaje_general()
            item.save()

        # ✅ Actualizar workflow de la evaluación según progreso real (DENTRO del POST)
        total_items = EvaluacionMiembro.objects.filter(evaluacion=evaluacion).count()
        total_evaluados = EvaluacionMiembro.objects.filter(
            evaluacion=evaluacion,
            evaluado_por__isnull=False
        ).count()

        if total_evaluados > 0 and evaluacion.estado_workflow == EvaluacionUnidad.ESTADO_BORRADOR:
            evaluacion.estado_workflow = EvaluacionUnidad.ESTADO_EN_PROGRESO
            evaluacion.save(update_fields=["estado_workflow"])

        if total_items > 0 and total_items == total_evaluados:
            evaluacion.estado_workflow = EvaluacionUnidad.ESTADO_CERRADA
            evaluacion.save(update_fields=["estado_workflow"])

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


@login_required
@require_POST
@csrf_protect
def guardar_evaluacion_miembro(request):
    """
    Vista AJAX para guardar la evaluación de un miembro individual.
    """
    try:
        data = json.loads(request.body)
        
        evaluacion_id = data.get('evaluacion_id')
        miembro_id = data.get('miembro_id')
        item_id = data.get('item_id')
        
        if not all([evaluacion_id, miembro_id, item_id]):
            return JsonResponse({
                'success': False,
                'error': 'Faltan datos requeridos'
            }, status=400)
        
        # Buscar el item de evaluación
        try:
            item = EvaluacionMiembro.objects.select_related(
                'evaluacion', 'evaluacion__perfil', 'evaluacion__unidad'
            ).get(
                id=item_id,
                evaluacion_id=evaluacion_id,
                miembro_id=miembro_id
            )
        except EvaluacionMiembro.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Evaluación no encontrada'
            }, status=404)
        
        evaluacion = item.evaluacion
        
        # ✅ PRIMERO: Verificar si está cerrada ANTES de intentar guardar
        if evaluacion and evaluacion.estado_workflow == EvaluacionUnidad.ESTADO_CERRADA:
            return JsonResponse({
                'success': False,
                'error': 'Esta evaluación está cerrada. Debes reabrirla para editar.'
            }, status=403)
        
        # ✅ Asegurar que la evaluación tenga perfil
        if evaluacion and not evaluacion.perfil:
            perfil, _ = EvaluacionPerfilUnidad.objects.get_or_create(unidad=evaluacion.unidad)
            evaluacion.perfil = perfil
            evaluacion.save(update_fields=["perfil"])
        
        # Actualizar campos organizacionales
        item.asistencia = int(data.get('asistencia', 3))
        item.participacion = int(data.get('participacion', 3))
        item.compromiso = int(data.get('compromiso', 3))
        item.actitud = int(data.get('actitud', 3))
        item.integracion = int(data.get('integracion', 3))
        
        # Liderazgo
        if hasattr(item, 'liderazgo'):
            item.liderazgo = int(data.get('liderazgo', 3))
        
        # Campo espiritual numérico
        item.madurez_espiritual = int(data.get('madurez_espiritual', 3))
        
        # Observación (opcional)
        item.observacion = data.get('observacion', '') or ''
        
        # Marcar quién evaluó
        item.evaluado_por = request.user
        
        # Guardar (recalcula puntaje automáticamente en save())
        item.save()
        
        # ✅ Actualizar workflow: BORRADOR -> EN_PROGRESO
        if evaluacion and evaluacion.estado_workflow == EvaluacionUnidad.ESTADO_BORRADOR:
            evaluacion.estado_workflow = EvaluacionUnidad.ESTADO_EN_PROGRESO
            evaluacion.save(update_fields=["estado_workflow"])

        # ✅ NO cerrar automáticamente al 100% - dejar que el usuario decida
        # Esto evita el problema de que se cierre cuando reabres y guardas

        return JsonResponse({
            'success': True,
            'puntaje_general': item.puntaje_general,
            'miembro_id': miembro_id,
            'item_id': item_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
        
    except Exception as e:
        import traceback
        print(f"Error en guardar_evaluacion_miembro: {e}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    

@login_required
@require_POST
@csrf_protect
def reabrir_evaluacion_unidad(request, evaluacion_id):
    """
    Reabre una evaluación cerrada:
    CERRADA -> EN_PROGRESO
    """
    evaluacion = get_object_or_404(EvaluacionUnidad, id=evaluacion_id)

    # ✅ Seguridad mínima (luego la hacemos más estricta si quieres):
    # Solo el creador o superusuario (puedes cambiar esta regla)
    if not (request.user.is_superuser or evaluacion.creado_por_id == request.user.id):
        return HttpResponseForbidden("No tienes permiso para reabrir esta evaluación.")

    # Solo reabrir si está cerrada
    if evaluacion.estado_workflow != EvaluacionUnidad.ESTADO_CERRADA:
        messages.info(request, "Esta evaluación no está cerrada, no hace falta reabrirla.")
        return redirect("evaluaciones_app:ver_resultados_unidad", evaluacion_id=evaluacion.id)

    # ✅ Reabrir: pasa a EN_PROGRESO
    evaluacion.estado_workflow = EvaluacionUnidad.ESTADO_EN_PROGRESO
    evaluacion.save(update_fields=["estado_workflow"])

    messages.success(request, "✅ Evaluación reabierta. Puedes seguir editándola.")
    return redirect("evaluaciones_app:evaluar_unidad", unidad_id=evaluacion.unidad_id)


@login_required
@require_POST
@csrf_protect
def cerrar_evaluacion_unidad(request, evaluacion_id):
    """
    Cierra una evaluación manualmente:
    EN_PROGRESO -> CERRADA
    """
    evaluacion = get_object_or_404(EvaluacionUnidad, id=evaluacion_id)

    # Seguridad: solo el creador o superusuario
    if not (request.user.is_superuser or evaluacion.creado_por_id == request.user.id):
        return HttpResponseForbidden("No tienes permiso para cerrar esta evaluación.")

    # Solo cerrar si está en progreso
    if evaluacion.estado_workflow == EvaluacionUnidad.ESTADO_CERRADA:
        messages.info(request, "Esta evaluación ya está cerrada.")
        return redirect("evaluaciones_app:ver_resultados_unidad", evaluacion_id=evaluacion.id)

    # ✅ Cerrar evaluación
    evaluacion.estado_workflow = EvaluacionUnidad.ESTADO_CERRADA
    evaluacion.save(update_fields=["estado_workflow"])

    messages.success(request, "✅ Evaluación cerrada correctamente.")
    return redirect("evaluaciones_app:ver_resultados_unidad", evaluacion_id=evaluacion.id)


@login_required
def listar_evaluaciones_unidad(request, unidad_id):
    """
    Lista todas las evaluaciones de una unidad (útil para modo libre).
    """
    unidad = get_object_or_404(Unidad, id=unidad_id)
    perfil, _ = EvaluacionPerfilUnidad.objects.get_or_create(unidad=unidad)

    evaluaciones = EvaluacionUnidad.objects.filter(
        unidad=unidad
    ).order_by('-anio', '-mes', '-numero_secuencia')

    evaluaciones_cerradas = evaluaciones.filter(
        estado_workflow=EvaluacionUnidad.ESTADO_CERRADA
    ).count()

    evaluaciones_activas = evaluaciones.filter(
        estado_workflow__in=[
            EvaluacionUnidad.ESTADO_BORRADOR,
            EvaluacionUnidad.ESTADO_EN_PROGRESO
        ]
    ).count()

    context = {
        "unidad": unidad,
        "perfil": perfil,
        "evaluaciones": evaluaciones,
        "evaluaciones_cerradas": evaluaciones_cerradas,
        "evaluaciones_activas": evaluaciones_activas,
    }
    return render(request, "evaluaciones_app/listar_evaluaciones_unidad.html", context)


@login_required
@require_POST
@csrf_protect
def crear_nueva_evaluacion_libre(request, unidad_id):
    """
    Crea una nueva evaluación en modo libre para la unidad.
    """
    unidad = get_object_or_404(Unidad, id=unidad_id)
    perfil, _ = EvaluacionPerfilUnidad.objects.get_or_create(unidad=unidad)

    if not perfil.es_libre:
        messages.error(request, "Esta unidad está en modo automático. No puedes crear evaluaciones manualmente.")
        return redirect("evaluaciones_app:mis_unidades")

    hoy = timezone.now()

    # Crear nueva evaluación (el save() auto-calcula numero_secuencia)
    evaluacion = EvaluacionUnidad.objects.create(
        unidad=unidad,
        anio=hoy.year,
        mes=hoy.month,
        perfil=perfil,
        creado_por=request.user,
    )

    messages.success(request, f"✅ Nueva evaluación #{evaluacion.numero_secuencia} creada.")
    return redirect("evaluaciones_app:evaluar_unidad", unidad_id=unidad.id, evaluacion_id=evaluacion.id)