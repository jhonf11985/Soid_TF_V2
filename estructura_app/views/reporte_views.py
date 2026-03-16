from collections import defaultdict
from datetime import date, datetime
from types import SimpleNamespace
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from estructura_app.forms import ReporteCierreForm, ReportePeriodoForm
from estructura_app.models import (
    ActividadUnidad,
    ReporteUnidadCierre,
    ReporteUnidadPeriodo,
    RolUnidad,
    Unidad,
    UnidadCargo,
    UnidadMembresia,
)
from estructura_app.view_helpers.common import _require_tenant
from estructura_app.view_helpers.unidad_helpers import _get_edad_value


def _to_int(v):
    try:
        if v is None or v == "":
            return 0
        return int(v)
    except Exception:
        return 0


MESES = [
    (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
    (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
    (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
]

TRIMESTRES = [
    (1, "Q1 (Ene–Mar)"),
    (2, "Q2 (Abr–Jun)"),
    (3, "Q3 (Jul–Sep)"),
    (4, "Q4 (Oct–Dic)"),
]


def _rango_mes(anio: int, mes: int):
    inicio = timezone.datetime(anio, mes, 1).date()
    if mes == 12:
        fin = timezone.datetime(anio + 1, 1, 1).date()
    else:
        fin = timezone.datetime(anio, mes + 1, 1).date()
    return inicio, fin


def _generar_resumen_periodo(tenant, unidad, anio, mes):
    actividades = (
        ActividadUnidad.objects
        .filter(tenant=tenant, unidad=unidad, fecha__year=anio, fecha__month=mes)
        .prefetch_related("participantes")
    )

    participantes_ids = set()
    oyentes_total = 0
    nuevos_creyentes_total = 0

    for act in actividades:
        participantes_ids.update(act.participantes.values_list("id", flat=True))
        datos = act.datos or {}
        oyentes_total += int(datos.get("oyentes", 0))
        nuevos_creyentes_total += int(datos.get("nuevos_creyentes", 0))

    return {
        "actividades_total": actividades.count(),
        "participantes_unicos": len(participantes_ids),
        "oyentes_total": oyentes_total,
        "nuevos_creyentes_total": nuevos_creyentes_total,
        "alcanzados_total": oyentes_total,
    }


def _historico_reportes_unidad(tenant, unidad):
    mensuales = (
        ReporteUnidadPeriodo.objects
        .filter(tenant=tenant, unidad=unidad)
        .only("id", "anio", "mes", "resumen", "reflexion", "necesidades", "plan_proximo")
    )

    cierres = (
        ReporteUnidadCierre.objects
        .filter(tenant=tenant, unidad=unidad)
        .only("id", "anio", "tipo", "trimestre", "resumen", "reflexion", "necesidades", "plan_proximo")
    )

    def _key(r):
        mes = getattr(r, "mes", None)
        if mes is not None:
            return (int(r.anio), 1, int(mes))

        pt = (getattr(r, "tipo", "") or "").strip().lower()

        if pt == "trimestre":
            tri = int(getattr(r, "trimestre", 0) or 0)
            return (int(r.anio), 2, tri)

        if pt == "anio":
            return (int(r.anio), 3, 0)

        return (int(r.anio), 9, 0)

    lista = list(mensuales) + list(cierres)
    lista.sort(key=_key, reverse=True)

    return lista


def _meses_de_trimestre(tri: int):
    tri = int(tri)
    if tri == 1:
        return [1, 2, 3]
    if tri == 2:
        return [4, 5, 6]
    if tri == 3:
        return [7, 8, 9]
    return [10, 11, 12]


def _generar_resumen_trimestre(tenant, unidad, anio: int, tri: int):
    meses = _meses_de_trimestre(tri)

    actividades = (
        ActividadUnidad.objects
        .filter(tenant=tenant, unidad=unidad, fecha__year=anio, fecha__month__in=meses)
        .prefetch_related("participantes")
    )

    participantes_ids = set()
    oyentes_total = 0
    nuevos_creyentes_total = 0

    for act in actividades:
        participantes_ids.update(act.participantes.values_list("id", flat=True))
        datos = act.datos or {}
        oyentes_total += int(datos.get("oyentes", 0))
        nuevos_creyentes_total += int(datos.get("nuevos_creyentes", 0))

    return {
        "actividades_total": actividades.count(),
        "participantes_unicos": len(participantes_ids),
        "oyentes_total": oyentes_total,
        "nuevos_creyentes_total": nuevos_creyentes_total,
        "alcanzados_total": oyentes_total,
    }


def _generar_resumen_anual(tenant, unidad, anio: int):
    actividades = (
        ActividadUnidad.objects
        .filter(tenant=tenant, unidad=unidad, fecha__year=anio)
        .prefetch_related("participantes")
    )

    participantes_ids = set()
    oyentes_total = 0
    nuevos_creyentes_total = 0

    for act in actividades:
        participantes_ids.update(act.participantes.values_list("id", flat=True))
        datos = act.datos or {}
        oyentes_total += int(datos.get("oyentes", 0))
        nuevos_creyentes_total += int(datos.get("nuevos_creyentes", 0))

    return {
        "actividades_total": actividades.count(),
        "participantes_unicos": len(participantes_ids),
        "oyentes_total": oyentes_total,
        "nuevos_creyentes_total": nuevos_creyentes_total,
        "alcanzados_total": oyentes_total,
    }


def _rango_trimestre(anio: int, tri: int):
    mes_inicio = (tri - 1) * 3 + 1
    inicio = date(anio, mes_inicio, 1)
    if tri == 4:
        fin = date(anio + 1, 1, 1)
    else:
        fin = date(anio, mes_inicio + 3, 1)
    return inicio, fin


def _rango_anio(anio: int):
    return date(anio, 1, 1), date(anio + 1, 1, 1)


# ============================================================
# VISTAS DE REPORTES
# ============================================================

@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def unidad_reportes(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    hoy = timezone.localdate()
    anio_sel = int(request.GET.get("anio") or hoy.year)

    periodo_tipo = (request.GET.get("tipo") or "mes").strip().lower()
    if periodo_tipo not in ("mes", "trimestre", "anio"):
        periodo_tipo = "mes"

    mes_sel = int(request.GET.get("mes") or hoy.month)
    trimestre_sel = int(request.GET.get("tri") or ((hoy.month - 1) // 3 + 1))
    if trimestre_sel not in (1, 2, 3, 4):
        trimestre_sel = 1

    # TRIMESTRAL
    if periodo_tipo == "trimestre":
        cierre, _ = ReporteUnidadCierre.objects.get_or_create(
            tenant=tenant, unidad=unidad, anio=anio_sel,
            tipo="trimestre", trimestre=trimestre_sel,
            defaults={"creado_por": request.user},
        )

        es_post_reflexion = any(k in request.POST for k in ("reflexion", "necesidades", "plan_proximo"))

        if request.method == "POST" and not es_post_reflexion:
            cierre.resumen = _generar_resumen_trimestre(tenant, unidad, anio_sel, trimestre_sel)
            if not cierre.creado_por:
                cierre.creado_por = request.user
            cierre.save()
            messages.success(request, "Resumen trimestral recalculado.")
            return redirect(f"{request.path}?tipo=trimestre&anio={anio_sel}&tri={trimestre_sel}")

        if not cierre.resumen or (cierre.resumen or {}).get("actividades_total") is None:
            cierre.resumen = _generar_resumen_trimestre(tenant, unidad, anio_sel, trimestre_sel)
            if not cierre.creado_por:
                cierre.creado_por = request.user
            cierre.save()

        form = ReporteCierreForm(request.POST or None, instance=cierre)
        if request.method == "POST" and es_post_reflexion:
            if form.is_valid():
                form.save()
                messages.success(request, "Reporte trimestral guardado.")
                return redirect(f"{request.path}?tipo=trimestre&anio={anio_sel}&tri={trimestre_sel}")

        reportes_lista = _historico_reportes_unidad(tenant, unidad)
        resumen_vista = cierre.resumen or {}

        return render(request, "estructura_app/unidad_reportes.html", {
            "unidad": unidad,
            "reportes_lista": reportes_lista,
            "reporte": cierre,
            "form": form,
            "anio_sel": anio_sel,
            "mes_sel": mes_sel,
            "MESES": MESES,
            "periodo_tipo": periodo_tipo,
            "trimestre_sel": trimestre_sel,
            "TRIMESTRES": TRIMESTRES,
            "resumen_vista": resumen_vista,
        })

    # ANUAL
    if periodo_tipo == "anio":
        cierre, _ = ReporteUnidadCierre.objects.get_or_create(
            tenant=tenant, unidad=unidad, anio=anio_sel,
            tipo="anio", trimestre=None,
            defaults={"creado_por": request.user},
        )

        es_post_reflexion = any(k in request.POST for k in ("reflexion", "necesidades", "plan_proximo"))

        if request.method == "POST" and not es_post_reflexion:
            cierre.resumen = _generar_resumen_anual(tenant, unidad, anio_sel)
            if not cierre.creado_por:
                cierre.creado_por = request.user
            cierre.save()
            messages.success(request, "Resumen anual recalculado.")
            return redirect(f"{request.path}?tipo=anio&anio={anio_sel}")

        if not cierre.resumen or (cierre.resumen or {}).get("actividades_total") is None:
            cierre.resumen = _generar_resumen_anual(tenant, unidad, anio_sel)
            if not cierre.creado_por:
                cierre.creado_por = request.user
            cierre.save()

        form = ReporteCierreForm(request.POST or None, instance=cierre)
        if request.method == "POST" and es_post_reflexion:
            if form.is_valid():
                form.save()
                messages.success(request, "Reporte anual guardado.")
                return redirect(f"{request.path}?tipo=anio&anio={anio_sel}")

        reportes_lista = _historico_reportes_unidad(tenant, unidad)
        resumen_vista = cierre.resumen or {}

        return render(request, "estructura_app/unidad_reportes.html", {
            "unidad": unidad,
            "reportes_lista": reportes_lista,
            "reporte": cierre,
            "form": form,
            "anio_sel": anio_sel,
            "mes_sel": mes_sel,
            "MESES": MESES,
            "periodo_tipo": periodo_tipo,
            "trimestre_sel": trimestre_sel,
            "TRIMESTRES": TRIMESTRES,
            "resumen_vista": resumen_vista,
        })

    # MENSUAL
    reporte, _created = ReporteUnidadPeriodo.objects.get_or_create(
        tenant=tenant, unidad=unidad, anio=anio_sel, mes=mes_sel,
        defaults={"creado_por": request.user},
    )

    es_post_reflexion = any(k in request.POST for k in ("reflexion", "necesidades", "plan_proximo"))

    if request.method == "POST" and not es_post_reflexion:
        reporte.resumen = _generar_resumen_periodo(tenant, unidad, anio_sel, mes_sel)
        if not reporte.creado_por:
            reporte.creado_por = request.user
        reporte.save()
        messages.success(request, "Resumen recalculado.")
        return redirect(f"{request.path}?tipo=mes&anio={anio_sel}&mes={mes_sel}")

    if not reporte.resumen or (reporte.resumen or {}).get("actividades_total") is None:
        reporte.resumen = _generar_resumen_periodo(tenant, unidad, anio_sel, mes_sel)
        if not reporte.creado_por:
            reporte.creado_por = request.user
        reporte.save()

    form = ReportePeriodoForm(request.POST or None, instance=reporte)
    if request.method == "POST" and es_post_reflexion:
        if form.is_valid():
            form.save()
            messages.success(request, "Reporte guardado.")
            return redirect(f"{request.path}?tipo=mes&anio={anio_sel}&mes={mes_sel}")

    reportes_lista = _historico_reportes_unidad(tenant, unidad)
    resumen_vista = reporte.resumen or {}

    return render(request, "estructura_app/unidad_reportes.html", {
        "unidad": unidad,
        "reportes_lista": reportes_lista,
        "reporte": reporte,
        "form": form,
        "anio_sel": anio_sel,
        "mes_sel": mes_sel,
        "MESES": MESES,
        "periodo_tipo": periodo_tipo,
        "trimestre_sel": trimestre_sel,
        "TRIMESTRES": TRIMESTRES,
        "resumen_vista": resumen_vista,
    })


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def reporte_unidad_imprimir(request, pk, anio, mes):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)
    anio = int(anio)
    mes = int(mes)

    periodo_tipo = (request.GET.get("tipo") or "mes").strip().lower()
    if periodo_tipo not in ("mes", "trimestre", "anio"):
        periodo_tipo = "mes"

    trimestre_sel = int(request.GET.get("tri") or ((mes - 1) // 3 + 1))
    if trimestre_sel not in (1, 2, 3, 4):
        trimestre_sel = 1

    mes_nombre = dict(MESES).get(mes, str(mes))

    if periodo_tipo == "anio":
        periodo_label = "anual"
        periodo_texto = f"Año {anio}"
    elif periodo_tipo == "trimestre":
        periodo_label = "trimestral"
        TRIMESTRES_TEXTO = {1: "Ene–Mar", 2: "Abr–Jun", 3: "Jul–Sep", 4: "Oct–Dic"}
        periodo_texto = f"{TRIMESTRES_TEXTO.get(trimestre_sel, '—')} / {anio}"
    else:
        periodo_label = "mensual"
        periodo_texto = f"{mes_nombre} {anio}"

    if periodo_tipo == "mes":
        reporte, _ = ReporteUnidadPeriodo.objects.get_or_create(
            tenant=tenant, unidad=unidad, anio=anio, mes=mes,
            defaults={"creado_por": request.user},
        )
        if request.GET.get("refresh") == "1" or not reporte.resumen:
            reporte.resumen = _generar_resumen_periodo(tenant, unidad, anio, mes)
            reporte.save()
    else:
        if periodo_tipo == "trimestre":
            reporte, _ = ReporteUnidadCierre.objects.get_or_create(
                tenant=tenant, unidad=unidad, anio=anio,
                tipo="trimestre", trimestre=trimestre_sel,
                defaults={"creado_por": request.user},
            )
            if request.GET.get("refresh") == "1" or not reporte.resumen:
                reporte.resumen = _generar_resumen_trimestre(tenant, unidad, anio, trimestre_sel)
                reporte.save()
        else:
            reporte, _ = ReporteUnidadCierre.objects.get_or_create(
                tenant=tenant, unidad=unidad, anio=anio,
                tipo="anio", trimestre=None,
                defaults={"creado_por": request.user},
            )
            if request.GET.get("refresh") == "1" or not reporte.resumen:
                reporte.resumen = _generar_resumen_anual(tenant, unidad, anio)
                reporte.save()

    if periodo_tipo == "trimestre":
        resumen = _generar_resumen_trimestre(tenant, unidad, anio, trimestre_sel)
    else:
        resumen = _generar_resumen_anual(tenant, unidad, anio)

    reporte_virtual = SimpleNamespace(
        resumen=resumen or {},
        reflexion="",
        necesidades="",
        plan_proximo="",
    )

    return render(request, "estructura_app/reportes/reporte_unidad_periodo.html", {
        "unidad": unidad,
        "reporte": reporte_virtual,
        "mes_nombre": mes_nombre,
        "periodo_tipo": periodo_tipo,
        "periodo_label": periodo_label,
        "periodo_texto": periodo_texto,
        "trimestre_sel": trimestre_sel,
        "anio_sel": anio,
        "mes_sel": mes,
    })


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def reporte_unidad_padron_imprimir(request, pk, anio, mes):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    try:
        anio = int(anio)
    except Exception:
        anio = timezone.now().year

    try:
        mes = int(mes)
        if mes < 1 or mes > 12:
            mes = timezone.now().month
    except Exception:
        mes = timezone.now().month

    MESES_MAP = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }
    periodo_texto = f"{MESES_MAP.get(mes, str(mes))} {anio}"

    membresias = (
        UnidadMembresia.objects
        .filter(tenant=tenant, unidad=unidad, activo=True)
        .select_related("miembo_fk", "rol")
        .order_by("rol__orden", "rol__nombre", "miembo_fk__nombres", "miembo_fk__apellidos")
    )

    cargos = (
        UnidadCargo.objects
        .filter(tenant=tenant, unidad=unidad, vigente=True, rol__tipo=RolUnidad.TIPO_LIDERAZGO)
        .select_related("miembo_fk", "rol")
        .order_by("rol__orden", "rol__nombre", "miembo_fk__nombres", "miembo_fk__apellidos")
    )

    def _edad(miembro):
        return _get_edad_value(miembro)

    def _genero_label_local(miembro):
        try:
            v = (miembro.get_genero_display() or "").strip()
            return v if v else "—"
        except Exception:
            v = (getattr(miembro, "genero", "") or "").strip()
            return v if v else "—"

    def _estado_label(miembro):
        estado_raw = (getattr(miembro, "estado_miembro", "") or "").strip()
        es_nuevo = bool(getattr(miembro, "nuevo_creyente", False))
        if estado_raw:
            try:
                return miembro.get_estado_miembro_display()
            except Exception:
                return estado_raw
        if es_nuevo:
            return "Nuevo creyente"
        return "No puede ser bautizado"

    lider_por_id = {}
    for c in cargos:
        lider_por_id[c.miembo_fk_id] = c

    filas = []
    ids_agregados = set()

    for mem in membresias:
        m = mem.miembo_fk
        if not m:
            continue
        ids_agregados.add(m.id)
        cargo = lider_por_id.get(m.id)
        es_lider = cargo is not None

        filas.append({
            "id": m.id,
            "codigo": getattr(m, "codigo_miembro", "") or "",
            "nombre": f"{m.nombres} {m.apellidos}".strip(),
            "edad": _edad(m),
            "genero": _genero_label_local(m),
            "estado": _estado_label(m),
            "nuevo": "Sí" if bool(getattr(m, "nuevo_creyente", False)) else "No",
            "rol": (cargo.rol.nombre if es_lider and cargo.rol else (mem.rol.nombre if mem.rol else "—")),
            "tipo": "Liderazgo" if es_lider else (
                "Trabajo" if (mem.rol and mem.rol.tipo == RolUnidad.TIPO_TRABAJO) else "Participación"
            ),
        })

    for c in cargos:
        m = c.miembo_fk
        if not m or m.id in ids_agregados:
            continue
        filas.append({
            "id": m.id,
            "codigo": getattr(m, "codigo_miembro", "") or "",
            "nombre": f"{m.nombres} {m.apellidos}".strip(),
            "edad": _edad(m),
            "genero": _genero_label_local(m),
            "estado": _estado_label(m),
            "nuevo": "Sí" if bool(getattr(m, "nuevo_creyente", False)) else "No",
            "rol": c.rol.nombre if c.rol else "—",
            "tipo": "Liderazgo",
        })

    filas.sort(key=lambda x: (x["nombre"] or "").lower())

    total = len(filas)
    activos = sum(1 for f in filas if (f["estado"] or "").strip().lower() == "activo")
    nuevos = sum(1 for f in filas if f["nuevo"] == "Sí")
    lideres = len(set(lider_por_id.keys()))

    context = {
        "unidad": unidad,
        "anio_sel": anio,
        "mes_sel": mes,
        "periodo_texto": periodo_texto,
        "periodo_label": "padrón",
        "total": total,
        "activos": activos,
        "nuevos": nuevos,
        "lideres": lideres,
        "filas": filas,
    }
    return render(request, "estructura_app/reportes/reporte_unidad_padron.html", context)


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def reporte_unidad_liderazgo_imprimir(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    cargos = (
        UnidadCargo.objects
        .select_related("miembo_fk", "rol")
        .filter(tenant=tenant, unidad=unidad, vigente=True, rol__tipo=RolUnidad.TIPO_LIDERAZGO)
        .order_by("rol__orden", "miembo_fk__nombres")
    )

    filas = []
    for c in cargos:
        m = c.miembo_fk
        estado_raw = (m.estado_miembro or "").strip()
        if estado_raw:
            estado_label = m.get_estado_miembro_display()
        else:
            estado_label = "Nuevo creyente" if m.nuevo_creyente else "No puede ser bautizado"

        filas.append({
            "rol": c.rol.nombre,
            "nombre": f"{m.nombres} {m.apellidos}",
            "codigo": m.codigo_miembro or "—",
            "edad": m.edad if m.edad is not None else "—",
            "telefono": m.telefono or "—",
            "estado": estado_label,
            "fecha_inicio": c.fecha_inicio,
        })

    reglas = unidad.reglas or {}

    context = {
        "unidad": unidad,
        "filas": filas,
        "total_lideres": len(filas),
        "lider_edad_min": reglas.get("lider_edad_min"),
        "lider_edad_max": reglas.get("lider_edad_max"),
    }
    return render(request, "estructura_app/reportes/reporte_unidad_liderazgo.html", context)


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def reporte_unidad_actividades_imprimir(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get("anio")) if request.GET.get("anio") else hoy.year
    except Exception:
        anio = hoy.year
    try:
        mes = int(request.GET.get("mes")) if request.GET.get("mes") else hoy.month
    except Exception:
        mes = hoy.month

    inicio = date(anio, mes, 1)
    fin = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)

    qs = (
        ActividadUnidad.objects
        .select_related("responsable")
        .filter(tenant=tenant, unidad=unidad, fecha__gte=inicio, fecha__lt=fin)
        .order_by("fecha", "id")
    )

    conteo_tipos = defaultdict(int)
    metric_keys = ["oyentes", "alcanzados", "nuevos_creyentes", "seguimientos"]
    metric_totals = {k: 0 for k in metric_keys}

    filas = []
    for a in qs:
        conteo_tipos[a.tipo] += 1
        datos = a.datos or {}
        for k in metric_keys:
            metric_totals[k] += _to_int(datos.get(k))

        responsable_nombre = str(a.responsable) if a.responsable else "—"
        resumen_partes = []
        if _to_int(datos.get("oyentes")):
            resumen_partes.append(f"Oyentes: {_to_int(datos.get('oyentes'))}")
        if _to_int(datos.get("alcanzados")):
            resumen_partes.append(f"Alcanzados: {_to_int(datos.get('alcanzados'))}")
        if _to_int(datos.get("nuevos_creyentes")):
            resumen_partes.append(f"Nuevos: {_to_int(datos.get('nuevos_creyentes'))}")
        if _to_int(datos.get("seguimientos")):
            resumen_partes.append(f"Seguimientos: {_to_int(datos.get('seguimientos'))}")

        filas.append({
            "fecha": a.fecha,
            "titulo": a.titulo,
            "tipo": a.get_tipo_display(),
            "lugar": a.lugar or "—",
            "responsable": responsable_nombre,
            "metricas": " · ".join(resumen_partes) if resumen_partes else "—",
        })

    tipos_display = []
    for code, label in ActividadUnidad.TIPOS:
        tipos_display.append({"code": code, "label": label, "count": int(conteo_tipos.get(code, 0))})

    return render(request, "estructura_app/reportes/reporte_unidad_actividades.html", {
        "unidad": unidad,
        "anio": anio,
        "mes": mes,
        "inicio": inicio,
        "fin": fin,
        "total_actividades": qs.count(),
        "tipos_display": tipos_display,
        "metric_totals": metric_totals,
        "filas": filas,
    })


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def reporte_unidad_cierre_imprimir(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    tipo = (request.GET.get("tipo") or "trimestre").strip().lower()
    if tipo not in ("trimestre", "anio"):
        tipo = "trimestre"

    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get("anio") or hoy.year)
    except Exception:
        anio = hoy.year

    tri = None
    if tipo == "trimestre":
        try:
            tri = int(request.GET.get("tri") or ((hoy.month - 1) // 3 + 1))
        except Exception:
            tri = 1
        if tri not in (1, 2, 3, 4):
            tri = 1

    if tipo == "anio":
        inicio, fin = _rango_anio(anio)
    else:
        inicio, fin = _rango_trimestre(anio, tri)

    cierre, created = ReporteUnidadCierre.objects.get_or_create(
        tenant=tenant, unidad=unidad, anio=anio, tipo=tipo,
        trimestre=tri if tipo == "trimestre" else None,
        defaults={
            "resumen": {},
            "reflexion": "",
            "necesidades": "",
            "plan_proximo": "",
            "creado_por": request.user,
        }
    )

    force_refresh = request.GET.get("refresh") == "1"
    if force_refresh or (not cierre.resumen):
        qs = (
            ActividadUnidad.objects
            .filter(tenant=tenant, unidad=unidad, fecha__gte=inicio, fecha__lt=fin)
            .order_by("fecha", "id")
        )

        conteo_tipos = defaultdict(int)
        metric_keys = ["oyentes", "alcanzados", "nuevos_creyentes", "seguimientos"]
        metric_totals = {k: 0 for k in metric_keys}

        for a in qs:
            conteo_tipos[a.tipo] += 1
            datos = a.datos or {}
            for k in metric_keys:
                metric_totals[k] += _to_int(datos.get(k))

        resumen = {
            "total_actividades": qs.count(),
            "por_tipo": dict(conteo_tipos),
            "metricas": metric_totals,
            "rango": {"inicio": str(inicio), "fin": str(fin)},
        }

        cierre.resumen = resumen
        cierre.save(update_fields=["resumen", "actualizado_en"])

    if tipo == "anio":
        periodo_texto = f"Año {anio}"
        badge = "Anual"
    else:
        periodo_texto = f"Trimestre {tri} - {anio}"
        badge = f"Q{tri}"

    return render(request, "estructura_app/reportes/reporte_unidad_cierre.html", {
        "unidad": unidad,
        "cierre": cierre,
        "periodo_texto": periodo_texto,
        "badge": badge,
        "inicio": inicio,
        "fin": fin,
    })


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def reporte_miembros_multi_unidad(request):
    tenant = _require_tenant(request)

    min_unidades = 2

    def _edad_miembro(m):
        try:
            return _get_edad_value(m)
        except Exception:
            return getattr(m, "edad", None)

    def _codigo_miembro(m):
        return getattr(m, "codigo_miembro", None) or ""

    def _estado_display(m):
        try:
            return m.get_estado_miembro_display() or ""
        except Exception:
            return getattr(m, "estado_miembro", "") or ""

    data = defaultdict(lambda: {
        "miembro": None,
        "unidades": {},
        "lider_unidades": set(),
    })

    qs_cargos = UnidadCargo.objects.filter(tenant=tenant, vigente=True).select_related("miembo_fk", "unidad", "rol")
    for c in qs_cargos:
        m = c.miembo_fk
        if not m or not c.unidad:
            continue
        d = data[m.id]
        d["miembro"] = m
        d["unidades"][c.unidad_id] = {"unidad": c.unidad, "etiqueta": "Liderazgo"}
        d["lider_unidades"].add(c.unidad_id)

    qs_mem = UnidadMembresia.objects.filter(tenant=tenant, activo=True).select_related("miembo_fk", "unidad", "rol")
    for mem in qs_mem:
        m = mem.miembo_fk
        if not m or not mem.unidad:
            continue
        d = data[m.id]
        d["miembro"] = m
        if mem.unidad_id in d["lider_unidades"]:
            continue
        etiqueta = "Membresía"
        try:
            if mem.rol and mem.rol.tipo == RolUnidad.TIPO_TRABAJO:
                etiqueta = "Trabajo"
            elif mem.rol and mem.rol.tipo == RolUnidad.TIPO_PARTICIPACION:
                etiqueta = "Participación"
        except Exception:
            pass
        if mem.unidad_id not in d["unidades"]:
            d["unidades"][mem.unidad_id] = {"unidad": mem.unidad, "etiqueta": etiqueta}

    filas = []
    for miembro_id, d in data.items():
        m = d["miembro"]
        if not m:
            continue
        total_unidades = len(d["unidades"])
        if total_unidades >= min_unidades:
            filas.append({
                "miembro_id": miembro_id,
                "nombre": f"{m.nombres} {m.apellidos}".strip(),
                "codigo": _codigo_miembro(m) or "—",
                "edad": _edad_miembro(m),
                "estado": _estado_display(m) or "—",
                "total_unidades": total_unidades,
                "items": list(d["unidades"].values()),
            })

    filas.sort(key=lambda x: (-x["total_unidades"], x["nombre"]))

    return render(request, "estructura_app/reportes/reporte_miembros_multi_unidad.html", {
        "min_unidades": min_unidades,
        "total": len(filas),
        "page_obj": filas,
        "q": "",
        "estado": "todos",
        "incluir_liderazgo": True,
        "incluir_membresia": True,
        "solo_vigentes": True,
        "excluir_nc": False,
        "per_page": 999999,
    })


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def reporte_unidad_historico_imprimir(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    desde = (request.GET.get("desde") or "").strip()
    hasta = (request.GET.get("hasta") or "").strip()

    def _parse_date(s):
        try:
            return date.fromisoformat(s)
        except Exception:
            return None

    desde_date = _parse_date(desde) if desde else None
    hasta_date = _parse_date(hasta) if hasta else None

    def _extraer_motivo_y_nota(texto: str):
        if not texto:
            return ("—", "")
        lineas = [l.strip() for l in str(texto).splitlines() if l.strip()]
        sello = ""
        for l in reversed(lineas):
            if "Motivo:" in l:
                sello = l
                break
        if not sello:
            return ("—", "")
        motivo = "—"
        m = re.search(r"Motivo:\s*([^|]+)", sello)
        if m:
            motivo = (m.group(1) or "").strip() or "—"
        nota = ""
        n = re.search(r"Nota:\s*(.+)$", sello)
        if n:
            nota = (n.group(1) or "").strip()
        return (motivo, nota)

    memb_qs = (
        UnidadMembresia.objects
        .filter(tenant=tenant, unidad=unidad, activo=False)
        .select_related("miembo_fk", "rol")
        .order_by("-fecha_salida", "-fecha_ingreso")
    )
    if desde_date:
        memb_qs = memb_qs.filter(fecha_salida__gte=desde_date)
    if hasta_date:
        memb_qs = memb_qs.filter(fecha_salida__lte=hasta_date)

    memb_rows = []
    for mem in memb_qs:
        persona = getattr(mem, "miembo_fk", None)
        nombre = "—"
        if persona:
            nombre = (f"{getattr(persona, 'nombres', '')} {getattr(persona, 'apellidos', '')}").strip() or str(persona)
        rol_nombre = getattr(getattr(mem, "rol", None), "nombre", None) or "—"
        motivo, nota = _extraer_motivo_y_nota(getattr(mem, "notas", "") or "")
        memb_rows.append({
            "miembro": nombre, "rol": rol_nombre,
            "fecha_ingreso": getattr(mem, "fecha_ingreso", None),
            "fecha_salida": getattr(mem, "fecha_salida", None),
            "motivo": motivo, "nota": nota,
            "notas_raw": getattr(mem, "notas", "") or "",
        })

    cargo_qs = (
        UnidadCargo.objects
        .filter(tenant=tenant, unidad=unidad, vigente=False, rol__tipo=RolUnidad.TIPO_LIDERAZGO)
        .select_related("miembo_fk", "rol")
        .order_by("-fecha_fin", "-fecha_inicio")
    )
    if desde_date:
        cargo_qs = cargo_qs.filter(fecha_fin__gte=desde_date)
    if hasta_date:
        cargo_qs = cargo_qs.filter(fecha_fin__lte=hasta_date)

    cargo_rows = []
    for cargo in cargo_qs:
        persona = getattr(cargo, "miembo_fk", None)
        nombre = "—"
        if persona:
            nombre = (f"{getattr(persona, 'nombres', '')} {getattr(persona, 'apellidos', '')}").strip() or str(persona)
        rol_nombre = getattr(getattr(cargo, "rol", None), "nombre", None) or "—"
        texto_notas = ""
        if hasattr(cargo, "notas"):
            texto_notas = getattr(cargo, "notas", "") or ""
        elif hasattr(cargo, "observaciones"):
            texto_notas = getattr(cargo, "observaciones", "") or ""
        motivo, nota = _extraer_motivo_y_nota(texto_notas)
        cargo_rows.append({
            "miembro": nombre, "cargo": rol_nombre,
            "fecha_inicio": getattr(cargo, "fecha_inicio", None),
            "fecha_fin": getattr(cargo, "fecha_fin", None),
            "motivo": motivo, "nota": nota,
            "notas_raw": texto_notas,
        })

    fecha_creacion = getattr(unidad, "creado_en", None) or getattr(unidad, "fecha_creacion", None)
    miembros_actuales = UnidadMembresia.objects.filter(tenant=tenant, unidad=unidad, activo=True).values_list("miembo_fk_id", flat=True).distinct().count()
    miembros_historicos = UnidadMembresia.objects.filter(tenant=tenant, unidad=unidad).values_list("miembo_fk_id", flat=True).distinct().count()
    total_salidas = memb_qs.count()
    lideres_actuales = UnidadCargo.objects.filter(tenant=tenant, unidad=unidad, vigente=True, rol__tipo=RolUnidad.TIPO_LIDERAZGO).values_list("miembo_fk_id", flat=True).distinct().count()
    lideres_historicos = UnidadCargo.objects.filter(tenant=tenant, unidad=unidad, rol__tipo=RolUnidad.TIPO_LIDERAZGO).values_list("miembo_fk_id", flat=True).distinct().count()
    total_cargos_terminados = cargo_qs.count()

    return render(request, "estructura_app/reportes/reporte_unidad_historico.html", {
        "unidad": unidad,
        "hoy": timezone.now().date(),
        "fecha_creacion": fecha_creacion,
        "desde": desde, "hasta": hasta,
        "memb_rows": memb_rows,
        "cargo_rows": cargo_rows,
        "miembros_actuales": miembros_actuales,
        "miembros_historicos": miembros_historicos,
        "total_salidas": total_salidas,
        "lideres_actuales": lideres_actuales,
        "lideres_historicos": lideres_historicos,
        "total_cargos_terminados": total_cargos_terminados,
    })