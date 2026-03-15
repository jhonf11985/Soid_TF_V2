from django.db.models import Q

from miembros_app.models import Miembro
from estructura_app.models import Unidad, UnidadCargo, UnidadMembresia, RolUnidad


def get_unidades_permitidas(user, tenant):
    """
    Unidades visibles para el usuario dentro del tenant.
    """
    if user.is_superuser or user.is_staff:
        return Unidad.objects.filter(tenant=tenant)

    if not user.has_perm("estructura_app.view_unidad"):
        return Unidad.objects.none()

    try:
        miembro = Miembro.objects.get(tenant=tenant, usuario=user)
    except Miembro.DoesNotExist:
        return Unidad.objects.none()

    unidades_liderazgo_ids = UnidadCargo.objects.filter(
        tenant=tenant,
        miembo_fk=miembro,
        vigente=True,
        rol__tipo=RolUnidad.TIPO_LIDERAZGO
    ).values_list("unidad_id", flat=True)

    unidades_membresia_ids = UnidadMembresia.objects.filter(
        tenant=tenant,
        miembo_fk=miembro,
        activo=True
    ).values_list("unidad_id", flat=True)

    return Unidad.objects.filter(
        tenant=tenant
    ).filter(
        Q(id__in=unidades_liderazgo_ids) | Q(id__in=unidades_membresia_ids)
    ).distinct()


def get_lideres_en_cadena(unidad):
    """
    Devuelve UnidadCargo heredado en cadena (padre -> abuelo -> ...),
    heredando TODOS los roles de tipo LIDERAZGO.
    Nota: no necesita tenant explícito porque filtra por unidad (que ya pertenece a un tenant).
    """
    if not unidad.padre:
        return UnidadCargo.objects.none()

    if hasattr(unidad, "hereda_lideres_padre") and not unidad.hereda_lideres_padre:
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

        if hasattr(padre, "hereda_lideres_padre") and not padre.hereda_lideres_padre:
            break

        padre = padre.padre

    return heredados


def get_lideres_heredados(unidad):
    """
    Variante heredada basada en el flag hereda_liderazgo.
    """
    lideres = UnidadCargo.objects.none()
    visitadas = set()
    padre = unidad.padre

    if not getattr(unidad, "hereda_liderazgo", True):
        return lideres

    while padre and padre.id not in visitadas:
        visitadas.add(padre.id)

        qs = UnidadCargo.objects.filter(
            unidad=padre,
            vigente=True,
            rol__tipo=RolUnidad.TIPO_LIDERAZGO
        )

        lideres = lideres.union(qs)

        if hasattr(padre, "hereda_liderazgo") and not padre.hereda_liderazgo:
            break

        padre = padre.padre

    return lideres