from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import redirect, render

from miembros_app.models import Miembro
from estructura_app.models import Unidad, TipoUnidad, RolUnidad, UnidadMembresia, UnidadCargo
from estructura_app.view_helpers.common import (
    _get_miembro_from_user,
    _get_unidades_lideradas_por_usuario,
    _require_tenant,
)


@login_required
@permission_required("estructura_app.view_unidad", raise_exception=True)
def estructura_home(request):
    return render(request, "estructura_app/home.html")


@login_required
def lider_home(request):
    tenant = _require_tenant(request)
    miembro = _get_miembro_from_user(request.user)

    if not miembro:
        messages.error(request, "Tu usuario no está vinculado a un miembro.")
        return render(request, "estructura_app/lider_home.html", {
            "unidades_info": [],
            "miembro": None,
        })

    unidades_info = _get_unidades_lideradas_por_usuario(request.user, tenant)

    return render(request, "estructura_app/lider_home.html", {
        "miembro": miembro,
        "unidades_info": unidades_info,
    })


@login_required
def dashboard(request):
    tenant = _require_tenant(request)
    u = request.user

    if not u.has_perm("estructura_app.ver_dashboard_estructura"):
        unidades_lideradas = _get_unidades_lideradas_por_usuario(u, tenant)

        if unidades_lideradas:
            return redirect("estructura_app:lider_home")

        if u.has_perm("estructura_app.view_unidad"):
            return redirect("estructura_app:unidad_listado")

        if u.has_perm("estructura_app.change_unidadmembresia"):
            return redirect("estructura_app:asignacion_unidad")

        if u.has_perm("estructura_app.view_rolunidad"):
            return redirect("estructura_app:rol_listado")

        raise PermissionDenied("No tienes permisos para acceder al módulo de Estructura.")

    total_unidades = Unidad.objects.filter(tenant=tenant).count()
    total_tipos = TipoUnidad.objects.filter(tenant=tenant, activo=True).count()
    total_roles = RolUnidad.objects.filter(tenant=tenant, activo=True).count()

    unidades_activas = Unidad.objects.filter(tenant=tenant, activa=True).count()
    unidades_inactivas = Unidad.objects.filter(tenant=tenant, activa=False).count()

    unidades_con_lider = (
        UnidadCargo.objects
        .filter(tenant=tenant, vigente=True, rol__tipo=RolUnidad.TIPO_LIDERAZGO)
        .values_list("unidad_id", flat=True)
        .distinct()
    )

    unidades_sin_lider = (
        Unidad.objects
        .filter(tenant=tenant, activa=True)
        .exclude(id__in=unidades_con_lider)
        .count()
    )

    top_unidades = (
        Unidad.objects
        .filter(tenant=tenant)
        .annotate(
            total_miembros=Count("membresias", filter=Q(membresias__activo=True))
        )
        .order_by("-total_miembros", "nombre")[:6]
    )

    distribucion_por_tipo = (
        TipoUnidad.objects
        .filter(tenant=tenant, activo=True)
        .annotate(total=Count("unidades"))
        .order_by("orden", "nombre")
    )

    total_miembros_oficiales = Miembro.objects.filter(
        tenant=tenant,
        activo=True,
        nuevo_creyente=False
    ).count()

    miembros_sirviendo = (
        UnidadMembresia.objects.filter(
            tenant=tenant,
            activo=True,
            rol__tipo=RolUnidad.TIPO_TRABAJO,
            miembo_fk__activo=True,
            miembo_fk__nuevo_creyente=False,
        )
        .values_list("miembo_fk_id", flat=True)
        .distinct()
        .count()
    )

    porcentaje_sirviendo = (
        round((miembros_sirviendo * 100) / total_miembros_oficiales, 1)
        if total_miembros_oficiales > 0
        else 0
    )

    miembros_no_sirviendo = max(total_miembros_oficiales - miembros_sirviendo, 0)

    porcentaje_no_sirviendo = (
        round((miembros_no_sirviendo * 100) / total_miembros_oficiales, 1)
        if total_miembros_oficiales > 0
        else 0
    )

    lideres_vigentes_personas = (
        UnidadCargo.objects.filter(
            tenant=tenant,
            vigente=True,
            rol__tipo=RolUnidad.TIPO_LIDERAZGO,
            miembo_fk__activo=True,
            miembo_fk__nuevo_creyente=False,
        )
        .values_list("miembo_fk_id", flat=True)
        .distinct()
        .count()
    )

    porcentaje_lideres = (
        round((lideres_vigentes_personas * 100) / total_miembros_oficiales, 1)
        if total_miembros_oficiales > 0
        else 0
    )

    context = {
        "total_unidades": total_unidades,
        "total_tipos": total_tipos,
        "total_roles": total_roles,
        "lideres_vigentes": lideres_vigentes_personas,
        "unidades_activas": unidades_activas,
        "unidades_inactivas": unidades_inactivas,
        "unidades_sin_lider": unidades_sin_lider,
        "top_unidades": top_unidades,
        "distribucion_por_tipo": distribucion_por_tipo,
        "miembros_sirviendo": miembros_sirviendo,
        "total_miembros_oficiales": total_miembros_oficiales,
        "porcentaje_sirviendo": porcentaje_sirviendo,
        "miembros_no_sirviendo": miembros_no_sirviendo,
        "porcentaje_no_sirviendo": porcentaje_no_sirviendo,
        "porcentaje_lideres": porcentaje_lideres,
    }
    return render(request, "estructura_app/dashboard.html", context)