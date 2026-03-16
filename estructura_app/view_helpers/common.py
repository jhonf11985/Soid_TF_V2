from django.http import Http404

from miembros_app.models import Miembro
from estructura_app.models import UnidadCargo, UnidadMembresia, RolUnidad


def _get_tenant(request):
    """Obtiene el tenant del request (asignado por middleware)."""
    return getattr(request, "tenant", None)


def _require_tenant(request):
    """Retorna tenant o lanza 404 si no existe."""
    tenant = _get_tenant(request)
    if not tenant:
        raise Http404("Tenant no configurado")
    return tenant


def _get_miembro_from_user(user):
    """
    Devuelve el Miembro vinculado al User.
    """
    try:
        m = Miembro.objects.filter(usuario=user).first()
        if m:
            return m
    except Exception:
        pass

    m = getattr(user, "miembro", None)
    if m:
        return m

    for attr in ("miembro_fk", "miembro_vinculado", "miembro_asociado"):
        m = getattr(user, attr, None)
        if m:
            return m

    perfil = getattr(user, "perfil", None)
    if perfil:
        m = getattr(perfil, "miembro", None)
        if m:
            return m

    return None


def _get_unidades_lideradas_por_usuario(user, tenant):
    """
    Devuelve las unidades donde el usuario es líder vigente.
    """
    miembro = _get_miembro_from_user(user)
    if not miembro:
        return []

    cargos = (
        UnidadCargo.objects
        .filter(tenant=tenant)
        .select_related("unidad", "rol", "unidad__tipo")
        .filter(
            miembo_fk=miembro,
            vigente=True,
            rol__tipo=RolUnidad.TIPO_LIDERAZGO,
        )
        .order_by("unidad__nombre", "rol__orden", "rol__nombre")
    )

    unidades_map = {}
    for cargo in cargos:
        if cargo.unidad_id not in unidades_map:
            unidades_map[cargo.unidad_id] = {
                "unidad": cargo.unidad,
                "cargo": cargo,
            }

    return list(unidades_map.values())


def _rol_en_uso(rol, tenant):
    """
    Indica si un rol está siendo usado en membresías o cargos.
    """
    en_membresias = UnidadMembresia.objects.filter(tenant=tenant, rol=rol).exists()
    en_cargos = UnidadCargo.objects.filter(tenant=tenant, rol=rol).exists()
    return en_membresias or en_cargos


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


