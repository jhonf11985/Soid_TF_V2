from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from miembros_app.models import Miembro
from estructura_app.forms import ActividadUnidadForm
from estructura_app.models import (
    ActividadUnidad,
    MovimientoUnidad,
    Unidad,
    UnidadCargo,
    UnidadMembresia,
    RolUnidad,
)
from estructura_app.view_helpers.common import _require_tenant
from estructura_app.view_helpers.permisos import (
    get_lideres_en_cadena,
    get_unidades_permitidas,
    _get_descendientes_heredados,
)
@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def unidad_listado(request):
    tenant = _require_tenant(request)
    query = request.GET.get("q", "").strip()

    unidades_permitidas = get_unidades_permitidas(request.user, tenant)

    unidades_qs = (
        unidades_permitidas
        .select_related("padre", "tipo")
        .annotate(
            total_miembros=Count(
                "membresias__miembo_fk",
                filter=Q(membresias__activo=True) & (
                    Q(membresias__rol__tipo__in=[RolUnidad.TIPO_PARTICIPACION, RolUnidad.TIPO_TRABAJO])
                    | Q(membresias__rol__isnull=True)
                ),
                distinct=True
            ),
            total_lideres=Count(
                "cargos",
                filter=Q(cargos__vigente=True, cargos__rol__tipo=RolUnidad.TIPO_LIDERAZGO),
                distinct=True
            ),
        )
    )

    if query:
        unidades_qs = unidades_qs.filter(
            Q(nombre__icontains=query) | Q(codigo__icontains=query)
        )

    # ══════════════════════════════════════════════════════════════
    # Ordenar jerárquicamente: padre seguido de sus hijos
    # ══════════════════════════════════════════════════════════════
    todas = list(unidades_qs.order_by("nombre"))
    
    # Separar padres (sin padre) e hijos
    padres = [u for u in todas if u.padre is None]
    hijos_por_padre = {}
    
    for u in todas:
        if u.padre_id:
            hijos_por_padre.setdefault(u.padre_id, []).append(u)
    
    # Construir lista ordenada: padre → hijos → padre → hijos...
    unidades_ordenadas = []
    ids_agregados = set()
    
    for padre in padres:
        unidades_ordenadas.append(padre)
        ids_agregados.add(padre.pk)
        
        # Agregar hijos de este padre
        for hijo in hijos_por_padre.get(padre.pk, []):
            unidades_ordenadas.append(hijo)
            ids_agregados.add(hijo.pk)
            
            # Agregar nietos (hijos del hijo) - segundo nivel
            for nieto in hijos_por_padre.get(hijo.pk, []):
                unidades_ordenadas.append(nieto)
                ids_agregados.add(nieto.pk)
    
    # Agregar huérfanos (hijos cuyo padre no está en la lista filtrada)
    for u in todas:
        if u.pk not in ids_agregados:
            unidades_ordenadas.append(u)

    return render(request, "estructura_app/unidad_listado.html", {
        "unidades": unidades_ordenadas,
        "query": query,
    })


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def unidad_detalle(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    # 🔐 PROTECCIÓN DE ACCESO POR UNIDAD (doble capa: permiso Django + filtro por unidades asignadas)
    unidades_permitidas = get_unidades_permitidas(request.user, tenant)
    if not unidades_permitidas.filter(id=unidad.id).exists():
        messages.error(request, "No tienes permiso para acceder a esta unidad.")
        return redirect("estructura_app:unidad_listado")

    lideres_asignados = UnidadCargo.objects.none()

    # =====================================================
    # 1) LISTA "MIEMBROS" (participación + sin rol)
    # =====================================================
    miembros_asignados = (
        UnidadMembresia.objects
        .filter(tenant=tenant, unidad=unidad, activo=True)
        .filter(Q(rol__tipo=RolUnidad.TIPO_PARTICIPACION) | Q(rol__isnull=True))
        .select_related("miembo_fk", "rol")
        .order_by("miembo_fk__nombres", "miembo_fk__apellidos")
    )

    # =====================================================
    # 2) LISTA "EQUIPO DE TRABAJO" (solo trabajo)
    # =====================================================
    equipo_trabajo_asignados = (
        UnidadMembresia.objects
        .filter(tenant=tenant, unidad=unidad, activo=True, rol__tipo=RolUnidad.TIPO_TRABAJO)
        .select_related("miembo_fk", "rol")
        .order_by("rol__orden", "rol__nombre", "miembo_fk__nombres", "miembo_fk__apellidos")
    )

    lideres_propios = (
        UnidadCargo.objects
        .filter(
            tenant=tenant,
            unidad=unidad,
            vigente=True,
            rol__tipo=RolUnidad.TIPO_LIDERAZGO,
        )
        .select_related("miembo_fk", "rol")
    )

    lideres_heredados = (
        get_lideres_en_cadena(unidad)
        .select_related("miembo_fk", "rol", "unidad")
    )

    ids_propios = set(lideres_propios.values_list("miembo_fk_id", flat=True))

    lideres_finales = []

    for c in lideres_propios:
        c.es_heredado = False
        lideres_finales.append(c)

    for c in lideres_heredados:
        if c.miembo_fk_id not in ids_propios:
            c.es_heredado = True
            lideres_finales.append(c)

    lideres_asignados = sorted(
        lideres_finales,
        key=lambda x: (x.rol.orden, x.rol.nombre, x.miembo_fk.nombres, x.miembo_fk.apellidos)
    )

    # =====================================================
    # 3) TOTAL REAL DE MIEMBROS
    # =====================================================
    miembros_total_asignados = (
        UnidadMembresia.objects
        .filter(tenant=tenant, unidad=unidad, activo=True)
        .filter(
            Q(rol__tipo__in=[RolUnidad.TIPO_PARTICIPACION, RolUnidad.TIPO_TRABAJO])
            | Q(rol__isnull=True)
        )
        .select_related("miembo_fk", "rol")
    )

    miembros_ids = list(
        miembros_total_asignados.values_list("miembo_fk_id", flat=True).distinct()
    )
    miembros = list(
        Miembro.objects.filter(tenant=tenant, id__in=miembros_ids).order_by("nombres", "apellidos")
    )

    total = len(miembros)

    # --- Género
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

    # --- Estados
    activos = pasivos = observacion = disciplina = catecumenos = 0
    menores_estado_vacio = nuevos_creyentes = 0

    for m in miembros:
        e = (m.estado_miembro or "").strip().lower()
        es_nuevo = bool(getattr(m, "nuevo_creyente", False))

        if e == "activo":
            activos += 1
        elif e == "pasivo":
            pasivos += 1
        elif e == "observacion":
            observacion += 1
        elif e == "disciplina":
            disciplina += 1
        elif e == "catecumeno":
            catecumenos += 1
        elif es_nuevo:
            nuevos_creyentes += 1
        else:
            menores_estado_vacio += 1

    menores = menores_estado_vacio
    mayores = total - menores

    # --- Categoría de edad
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
        "nuevos_creyentes": nuevos_creyentes,
        "menores_estado_vacio": menores_estado_vacio,
        "categorias_edad": categorias_edad,
    }

    # =====================================================
    # CAPACIDAD MÁXIMA
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

    # =====================================================
    # 4) FINANZAS BÁSICAS (TAB)
    # =====================================================
    hoy = timezone.localdate()

    try:
        f_anio = int(request.GET.get("anio") or hoy.year)
    except Exception:
        f_anio = hoy.year

    try:
        f_mes = int(request.GET.get("mes") or hoy.month)
    except Exception:
        f_mes = hoy.month

    # A) Movimientos MANUALES (Estructura)
    movimientos_manual_qs = (
        MovimientoUnidad.objects
        .filter(tenant=tenant, unidad=unidad, fecha__year=f_anio, fecha__month=f_mes)
        .order_by("-fecha", "-id")
    )
    movimientos_manual = movimientos_manual_qs[:50]

    ingresos_manual = movimientos_manual_qs.filter(
        tipo=MovimientoUnidad.TIPO_INGRESO, anulado=False
    ).aggregate(s=Sum("monto"))["s"] or 0

    egresos_manual = movimientos_manual_qs.filter(
        tipo=MovimientoUnidad.TIPO_EGRESO, anulado=False
    ).aggregate(s=Sum("monto"))["s"] or 0

    # B) Movimientos DESDE FINANZAS
    movimientos_finanzas = []
    ingresos_finanzas = 0
    egresos_finanzas = 0

    FINANZAS_APPS = ("finanzas_app",)
    finanzas_activo = any(
        (app == a or app.endswith(f".{a}")) for a in FINANZAS_APPS for app in settings.INSTALLED_APPS
    )

    if finanzas_activo:
        try:
            from finanzas_app.models import MovimientoFinanciero

            movimientos_finanzas_qs = (
                MovimientoFinanciero.objects
                .filter(tenant=tenant, unidad=unidad, fecha__year=f_anio, fecha__month=f_mes)
                .select_related("categoria")
                .order_by("-fecha", "-id")
            )

            movimientos_finanzas = movimientos_finanzas_qs[:50]

            base_ok = movimientos_finanzas_qs.exclude(estado="anulado")

            ingresos_finanzas = base_ok.filter(tipo="ingreso").aggregate(s=Sum("monto"))["s"] or 0
            egresos_finanzas = base_ok.filter(tipo="egreso").aggregate(s=Sum("monto"))["s"] or 0

        except Exception:
            movimientos_finanzas = []
            ingresos_finanzas = 0
            egresos_finanzas = 0

    # Totales combinados
    ingresos_total = ingresos_manual + ingresos_finanzas
    egresos_total = egresos_manual + egresos_finanzas
    balance = ingresos_total - egresos_total

    movimientos = movimientos_manual


    # =====================================================
    # 5) NUEVOS CREYENTES
    # =====================================================
    reglas = unidad.reglas or {}
    permite_nuevos = bool(reglas.get("permite_nuevos", False))

    nuevos_creyentes_asignados = UnidadMembresia.objects.none()

    if permite_nuevos:
        nuevos_creyentes_asignados = (
            UnidadMembresia.objects
            .filter(
                tenant=tenant,
                unidad=unidad,
                activo=True,
                miembo_fk__nuevo_creyente=True,
            )
            .filter(
                Q(miembo_fk__estado_miembro__isnull=True) |
                Q(miembo_fk__estado_miembro__exact="")
            )
            .select_related("miembo_fk", "rol")
            .order_by("miembo_fk__nombres", "miembo_fk__apellidos")
        )
    return render(request, "estructura_app/unidad_detalle.html", {
        "unidad": unidad,
        "miembros_asignados": miembros_asignados,
        "equipo_trabajo_asignados": equipo_trabajo_asignados,
        "lideres_asignados": lideres_asignados,
        "resumen": resumen,
        "movimientos": movimientos,
        "fin_anio": f_anio,
        "fin_mes": f_mes,
        "ingresos_total": ingresos_total,
        "egresos_total": egresos_total,
        "balance": balance,
        "movimientos_finanzas": movimientos_finanzas,
        "movimientos_manual": movimientos_manual,
        "permite_nuevos": permite_nuevos,
        "nuevos_creyentes_asignados": nuevos_creyentes_asignados,
        "miembros_count": total,

        "capacidad_maxima": capacidad_maxima,
        "capacidad_excedida": capacidad_excedida,
    })


@login_required
@permission_required("estructura_app.change_unidad", raise_exception=True)
@require_POST
def unidad_imagen_actualizar(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    if "imagen" in request.FILES:
        unidad.imagen = request.FILES["imagen"]
        unidad.save(update_fields=["imagen", "actualizado_en"])
        messages.success(request, "Imagen actualizada correctamente.")
    else:
        messages.warning(request, "No se seleccionó ninguna imagen.")

    return redirect("estructura_app:unidad_detalle", pk=unidad.pk)


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def unidad_actividades(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    actividades = (
        ActividadUnidad.objects
        .filter(tenant=tenant, unidad=unidad)
        .select_related("responsable")
        .prefetch_related("participantes")
        .order_by("-fecha", "-creado_en")
    )

    return render(request, "estructura_app/unidad_actividades.html", {
        "unidad": unidad,
        "actividades": actividades,
    })


@login_required
@permission_required("estructura_app.add_actividadunidad", raise_exception=True)
def actividad_crear(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)

    if request.method == "POST":
        form = ActividadUnidadForm(request.POST, unidad=unidad)
        if form.is_valid():
            act = form.save(commit=False)
            act.tenant = tenant
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
@permission_required("estructura_app.view_unidad", raise_exception=True)
def lider_home(request):
    tenant = _require_tenant(request)

    miembro = Miembro.objects.filter(tenant=tenant, usuario=request.user).first()

    unidades_info = []

    if miembro:
        cargos_directos = (
            UnidadCargo.objects
            .filter(
                tenant=tenant,
                miembo_fk=miembro,
                vigente=True,
                rol__tipo=RolUnidad.TIPO_LIDERAZGO,
                unidad__activa=True,
            )
            .select_related("unidad", "unidad__tipo", "unidad__padre", "rol")
            .order_by("unidad__nombre", "rol__orden", "rol__nombre")
        )

        unidades_agregadas = set()

        for cargo in cargos_directos:
            unidad = cargo.unidad

            if unidad.id not in unidades_agregadas:
                unidades_info.append({
                    "unidad": unidad,
                    "cargo": cargo,
                    "es_heredada": False,
                    "unidad_origen": None,
                    "rol_nombre": cargo.rol.nombre,
                })
                unidades_agregadas.add(unidad.id)

            descendientes = _get_descendientes_heredados(unidad)

            for hija in descendientes:
                if hija.id in unidades_agregadas:
                    continue

                unidades_info.append({
                    "unidad": hija,
                    "cargo": cargo,  # cargo origen
                    "es_heredada": True,
                    "unidad_origen": unidad,
                    "rol_nombre": f"{cargo.rol.nombre} (heredado)",
                })
                unidades_agregadas.add(hija.id)

    return render(request, "estructura_app/lider_home.html", {
        "miembro": miembro,
        "unidades_info": unidades_info,
    })