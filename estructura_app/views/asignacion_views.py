import json
import datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q

from miembros_app.models import Miembro
from estructura_app.models import Unidad, RolUnidad, UnidadMembresia, UnidadCargo
from estructura_app.view_helpers.common import _require_tenant
from estructura_app.view_helpers.jerarquia import get_unidades_con_nivel
from estructura_app.view_helpers.unidad_helpers import (
    _cumple_rango_edad,
    _cumple_rango_edad_liderazgo,
    _get_edad_value,
    _genero_label,
)


@login_required
@permission_required("estructura_app.change_unidadmembresia", raise_exception=True)
def asignacion_unidad(request):
    tenant = _require_tenant(request)
    unidades = get_unidades_con_nivel(tenant)
    roles = RolUnidad.objects.filter(tenant=tenant, activo=True)

    context = {
        "unidades": unidades,
        "roles": roles,
    }
    return render(request, "estructura_app/asignacion_unidad.html", context)


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def asignacion_unidad_contexto(request):
    tenant = _require_tenant(request)
    unidad_id = (request.GET.get("unidad_id") or "").strip()
    if not unidad_id:
        return JsonResponse({"ok": False, "error": "Falta unidad_id"}, status=400)

    rol_id = (request.GET.get("rol_id") or "").strip()

    unidad = get_object_or_404(Unidad, pk=unidad_id, tenant=tenant)
    reglas = unidad.reglas or {}

    rol = None
    rol_es_liderazgo = False
    if rol_id:
        try:
            rol = RolUnidad.objects.get(pk=rol_id, tenant=tenant)
            rol_es_liderazgo = (getattr(rol, "tipo", None) == RolUnidad.TIPO_LIDERAZGO)
        except RolUnidad.DoesNotExist:
            rol = None
            rol_es_liderazgo = False

    solo_activos = bool(reglas.get("solo_activos", False))

    membresias_actuales = (
        UnidadMembresia.objects
        .filter(tenant=tenant, unidad=unidad, activo=True)
        .select_related("rol")
    )
    miembros_membresia_ids = set(membresias_actuales.values_list("miembo_fk_id", flat=True))
    rol_membresia_por_miembro = {
        m.miembo_fk_id: (m.rol.nombre if m.rol else "")
        for m in membresias_actuales
    }

    cargos_actuales = (
        UnidadCargo.objects
        .filter(tenant=tenant, unidad=unidad, vigente=True)
        .select_related("rol")
    )
    miembros_cargo_ids = set(cargos_actuales.values_list("miembo_fk_id", flat=True))
    rol_cargo_por_miembro = {
        c.miembo_fk_id: (c.rol.nombre if c.rol else "")
        for c in cargos_actuales
    }

    miembros_actuales_count = len(miembros_membresia_ids)

    qs = Miembro.objects.filter(tenant=tenant, activo=True)

    admite_hombres = bool(reglas.get("admite_hombres", True))
    admite_mujeres = bool(reglas.get("admite_mujeres", True))

    if not rol_es_liderazgo:
        if admite_hombres and not admite_mujeres:
            qs = qs.filter(
                Q(genero__iexact="m") |
                Q(genero__iexact="masculino") |
                Q(genero__iexact="hombre")
            )
        elif admite_mujeres and not admite_hombres:
            qs = qs.filter(
                Q(genero__iexact="f") |
                Q(genero__iexact="femenino") |
                Q(genero__iexact="mujer")
            )
        elif not admite_hombres and not admite_mujeres:
            qs = qs.none()

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

        if reglas.get("permite_nuevos"):
            q |= (
                (Q(estado_miembro__isnull=True) | Q(estado_miembro="")) &
                Q(nuevo_creyente=True)
            )

        if reglas.get("permite_menores"):
            q |= (
                (Q(estado_miembro__isnull=True) | Q(estado_miembro="")) &
                Q(nuevo_creyente=False)
            )

        q &= ~Q(estado_miembro__iexact="descarriado")
        qs = qs.filter(q)

    qs = qs.order_by("nombres", "apellidos")

    personas = []

    for p in qs:
        if rol_es_liderazgo:
            if not _cumple_rango_edad_liderazgo(p, reglas):
                continue
        else:
            if not _cumple_rango_edad(p, unidad):
                continue

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
                estado_slug = "menor"
                estado_label = "No puede ser bautizado"

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
            "genero": _genero_label(p),
            "estado": estado_label,
            "estado_slug": estado_slug,
            "categoria": p.get_categoria_edad_display() if p.categoria_edad else "",
            "ya_en_unidad": ya_en_unidad,
            "rol_en_unidad": rol_en_unidad,
        })

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
@permission_required("estructura_app.view_unidad", raise_exception=True)
def asignacion_guardar_contexto(request):
    tenant = _require_tenant(request)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    unidad_id = str(payload.get("unidad_id", "")).strip()
    rol_id = str(payload.get("rol_id", "")).strip()

    if not unidad_id or not rol_id:
        return JsonResponse({"ok": False, "error": "Falta unidad o rol"}, status=400)

    get_object_or_404(Unidad, pk=unidad_id, tenant=tenant)
    get_object_or_404(RolUnidad, pk=rol_id, tenant=tenant)

    return JsonResponse({"ok": True})


@login_required
@require_POST
@permission_required("estructura_app.change_unidadmembresia", raise_exception=True)
def asignacion_aplicar(request):
    tenant = _require_tenant(request)

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

    unidad = get_object_or_404(Unidad, pk=unidad_id, tenant=tenant)
    rol = get_object_or_404(RolUnidad, pk=rol_id, tenant=tenant)

    clean_ids = []
    for x in miembro_ids:
        try:
            clean_ids.append(int(x))
        except Exception:
            pass

    if not clean_ids:
        return JsonResponse({"ok": False, "error": "Selección inválida"}, status=400)

    miembros = Miembro.objects.filter(tenant=tenant, id__in=clean_ids)

    reglas = unidad.reglas or {}
    capacidad_maxima = reglas.get("capacidad_maxima", None)

    warning_capacidad = None
    if capacidad_maxima is not None:
        try:
            capacidad_maxima = int(capacidad_maxima)
            actuales = UnidadMembresia.objects.filter(tenant=tenant, unidad=unidad, activo=True).count()
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

        if not permite_liderazgo:
            return JsonResponse({
                "ok": False,
                "error": "Esta unidad no permite liderazgo. Activa el switch 'Permite liderazgo' en la unidad."
            }, status=400)

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

        lider_edad_min = _to_int_or_none(reglas.get("lider_edad_min"))
        lider_edad_max = _to_int_or_none(reglas.get("lider_edad_max"))

        if lider_edad_min is not None or lider_edad_max is not None:
            fuera_rango_lider = []
            for m in miembros:
                edad_val = _get_edad_value(m)
                if edad_val is None:
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

        if limite_lideres is not None:
            actuales_lideres = UnidadCargo.objects.filter(
                tenant=tenant, unidad=unidad, vigente=True, rol__tipo=RolUnidad.TIPO_LIDERAZGO
            ).count()

            ya_lideres_ids = set(
                UnidadCargo.objects.filter(
                    tenant=tenant, unidad=unidad, vigente=True,
                    rol__tipo=RolUnidad.TIPO_LIDERAZGO, miembo_fk_id__in=clean_ids
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

        creados = 0
        reactivados = 0
        ya_existian = 0
        hoy = timezone.now().date()

        for m in miembros:
            otros = UnidadCargo.objects.filter(
                tenant=tenant, unidad=unidad, miembo_fk=m, vigente=True,
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
                tenant=tenant,
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

        return JsonResponse({
            "ok": True,
            "modo": "liderazgo",
            "creados": creados,
            "reactivados": reactivados,
            "ya_existian": ya_existian,
            "warning": warning_capacidad,
        })

    # =====================================================
    # PARTICIPACIÓN / TRABAJO
    # =====================================================
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
    hoy = timezone.now().date()

    for m in miembros:
        obj, created_obj = UnidadMembresia.objects.update_or_create(
            tenant=tenant,
            unidad=unidad,
            miembo_fk=m,
            defaults={
                "activo": True,
                "rol": rol,
            }
        )

        if created_obj:
            if hasattr(obj, "fecha_ingreso") and not obj.fecha_ingreso:
                obj.fecha_ingreso = hoy
            if hasattr(obj, "fecha_salida"):
                obj.fecha_salida = None
            obj.save(
                update_fields=["fecha_ingreso", "fecha_salida"]
                if hasattr(obj, "fecha_salida")
                else ["fecha_ingreso"]
            )
            creados += 1
        else:
            update_fields = []

            if hasattr(obj, "fecha_salida") and obj.fecha_salida is not None:
                obj.fecha_salida = None
                update_fields.append("fecha_salida")
                reactivados += 1
            else:
                ya_existian += 1

            if hasattr(obj, "fecha_ingreso") and not obj.fecha_ingreso:
                obj.fecha_ingreso = hoy
                update_fields.append("fecha_ingreso")

            if update_fields:
                obj.save(update_fields=update_fields)

    return JsonResponse({
        "ok": True,
        "modo": "membresia",
        "creados": creados,
        "reactivados": reactivados,
        "ya_existian": ya_existian,
        "warning": warning_capacidad,
    })


@login_required
@permission_required("estructura_app.change_unidadmembresia", raise_exception=True)
@require_POST
def asignacion_remover(request):
    tenant = _require_tenant(request)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    unidad_id = str(payload.get("unidad_id", "")).strip()
    rol_id = str(payload.get("rol_id", "")).strip()
    miembro_ids = payload.get("miembro_ids") or []

    fecha_salida = (payload.get("fecha_salida") or "").strip()
    motivo = (payload.get("motivo") or "").strip()
    notas_extra = (payload.get("notas") or "").strip()

    if not unidad_id or not rol_id:
        return JsonResponse({"ok": False, "error": "Falta unidad o rol"}, status=400)

    if not isinstance(miembro_ids, list) or not miembro_ids:
        return JsonResponse({"ok": False, "error": "No hay miembros seleccionados"}, status=400)

    if not fecha_salida or not motivo:
        return JsonResponse({"ok": False, "error": "Falta fecha de salida o motivo"}, status=400)

    try:
        fecha_salida_date = datetime.date.fromisoformat(fecha_salida)
    except Exception:
        return JsonResponse({"ok": False, "error": "Fecha inválida (usa formato YYYY-MM-DD)"}, status=400)

    unidad = get_object_or_404(Unidad, pk=unidad_id, tenant=tenant)
    rol = get_object_or_404(RolUnidad, pk=rol_id, tenant=tenant)

    clean_ids = []
    for x in miembro_ids:
        try:
            clean_ids.append(int(x))
        except Exception:
            pass

    if not clean_ids:
        return JsonResponse({"ok": False, "error": "Selección inválida"}, status=400)

    tipo = getattr(rol, "tipo", None)

    # LIDERAZGO
    if tipo == RolUnidad.TIPO_LIDERAZGO:
        qs = UnidadCargo.objects.filter(
            tenant=tenant, unidad=unidad, rol=rol,
            miembo_fk_id__in=clean_ids, vigente=True,
        )

        removidos = 0
        sello = f"[SALIDA MASIVA - LIDERAZGO] Fecha: {fecha_salida_date.isoformat()} | Motivo: {motivo}"
        if notas_extra:
            sello = sello + f" | Nota: {notas_extra}"

        for cargo in qs:
            cargo.vigente = False
            update_fields = ["vigente"]

            if hasattr(cargo, "fecha_fin"):
                cargo.fecha_fin = fecha_salida_date
                update_fields.append("fecha_fin")

            if hasattr(cargo, "notas"):
                cargo.notas = (cargo.notas.rstrip() + "\n" + sello) if cargo.notas else sello
                update_fields.append("notas")
            elif hasattr(cargo, "observaciones"):
                cargo.observaciones = (cargo.observaciones.rstrip() + "\n" + sello) if cargo.observaciones else sello
                update_fields.append("observaciones")

            cargo.save(update_fields=update_fields)
            removidos += 1

        return JsonResponse({
            "ok": True,
            "modo": "liderazgo",
            "removidos": removidos,
        })

    # PARTICIPACIÓN / TRABAJO
    if tipo not in (RolUnidad.TIPO_PARTICIPACION, RolUnidad.TIPO_TRABAJO):
        return JsonResponse({"ok": False, "error": "Tipo de rol no permitido para remoción"}, status=400)

    qs = UnidadMembresia.objects.filter(
        tenant=tenant, unidad=unidad,
        miembo_fk_id__in=clean_ids, activo=True,
    )

    removidos = 0
    sello = f"[SALIDA MASIVA] Fecha: {fecha_salida_date.isoformat()} | Motivo: {motivo}"
    if notas_extra:
        sello = sello + f" | Nota: {notas_extra}"

    for memb in qs:
        memb.activo = False
        memb.fecha_salida = fecha_salida_date

        if memb.notas:
            memb.notas = memb.notas.rstrip() + "\n" + sello
        else:
            memb.notas = sello

        memb.save(update_fields=["activo", "fecha_salida", "notas"])
        removidos += 1

    return JsonResponse({
        "ok": True,
        "modo": "membresia",
        "removidos": removidos,
    })