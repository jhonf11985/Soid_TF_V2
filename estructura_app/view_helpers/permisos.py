from miembros_app.models import Miembro
from estructura_app.models import Unidad, UnidadCargo, UnidadMembresia, RolUnidad
from collections import deque


def _get_descendientes_heredados(unidad):
    resultado = []
    visitadas = set()
    cola = deque([unidad])

    while cola:
        actual = cola.popleft()
        if actual.id in visitadas:
            continue
        visitadas.add(actual.id)

        hijas = Unidad.objects.filter(
            tenant=actual.tenant,
            padre=actual,
            activa=True,
        ).select_related("tipo", "padre")

        for hija in hijas:
            if hija.hereda_liderazgo:
                resultado.append(hija)
                cola.append(hija)

    return resultado


def _get_unidades_liderazgo_directo(miembro, tenant):
    return list(
        Unidad.objects.filter(
            tenant=tenant,
            cargos__miembo_fk=miembro,
            cargos__vigente=True,
            cargos__rol__tipo=RolUnidad.TIPO_LIDERAZGO,
        ).distinct()
    )


def get_unidades_permitidas(user, tenant):
    if user.is_superuser or user.is_staff:
        return Unidad.objects.filter(tenant=tenant)

    if not user.has_perm("estructura_app.view_unidad"):
        return Unidad.objects.none()

    try:
        miembro = Miembro.objects.get(tenant=tenant, usuario=user)
    except Miembro.DoesNotExist:
        return Unidad.objects.none()

    unidades_liderazgo_directo = _get_unidades_liderazgo_directo(miembro, tenant)
    ids_liderazgo = {u.id for u in unidades_liderazgo_directo}

    for unidad in unidades_liderazgo_directo:
        ids_liderazgo.update(u.id for u in _get_descendientes_heredados(unidad))

    unidades_membresia_ids = set(
        UnidadMembresia.objects.filter(
            tenant=tenant,
            miembo_fk=miembro,
            activo=True
        ).values_list("unidad_id", flat=True)
    )

    ids_finales = ids_liderazgo | unidades_membresia_ids

    return Unidad.objects.filter(
        tenant=tenant,
        id__in=ids_finales
    ).distinct()


def get_lideres_en_cadena(unidad):
    if not unidad.padre:
        return UnidadCargo.objects.none()

    if not unidad.hereda_liderazgo:
        return UnidadCargo.objects.none()

    heredados = UnidadCargo.objects.none()
    visitadas = set()
    padre = unidad.padre

    while padre and padre.id not in visitadas:
        visitadas.add(padre.id)

        qs = UnidadCargo.objects.filter(
            unidad=padre,
            vigente=True,
            rol__tipo=RolUnidad.TIPO_LIDERAZGO,
        )
        heredados = heredados.union(qs)

        if not padre.hereda_liderazgo:
            break

        padre = padre.padre

    return heredados