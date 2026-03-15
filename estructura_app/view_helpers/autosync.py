from django.utils import timezone

from miembros_app.models import Miembro
from estructura_app.models import UnidadMembresia, RolUnidad
from estructura_app.view_helpers.unidad_helpers import _cumple_rango_edad


def _miembro_cumple_reglas_unidad_automatica(miembro, unidad):
    """
    Evalúa si un miembro debe pertenecer automáticamente a una unidad.
    SOLO aplica a membresía base (UnidadMembresia), nunca a liderazgo.
    """
    reglas = unidad.reglas or {}

    if not getattr(miembro, "activo", False):
        return False

    estado_raw = (getattr(miembro, "estado_miembro", "") or "").strip().lower()
    es_nuevo = bool(getattr(miembro, "nuevo_creyente", False))

    if estado_raw == "descarriado":
        return False

    admite_hombres = bool(reglas.get("admite_hombres", True))
    admite_mujeres = bool(reglas.get("admite_mujeres", True))

    genero = (getattr(miembro, "genero", "") or "").strip().lower()

    es_hombre = genero in ("m", "masculino", "hombre")
    es_mujer = genero in ("f", "femenino", "mujer")

    if admite_hombres and not admite_mujeres:
        if not es_hombre:
            return False
    elif admite_mujeres and not admite_hombres:
        if not es_mujer:
            return False
    elif not admite_hombres and not admite_mujeres:
        return False

    if not _cumple_rango_edad(miembro, unidad):
        return False

    solo_activos = bool(reglas.get("solo_activos", False))
    permite_activos = bool(reglas.get("permite_activos", False))
    permite_observacion = bool(reglas.get("permite_observacion", False))
    permite_pasivos = bool(reglas.get("permite_pasivos", False))
    permite_disciplina = bool(reglas.get("permite_disciplina", False))
    permite_catecumenos = bool(reglas.get("permite_catecumenos", False))
    permite_nuevos = bool(reglas.get("permite_nuevos", False))
    permite_menores = bool(reglas.get("permite_menores", False))

    if solo_activos:
        return estado_raw == "activo"

    estados_permitidos = set()

    if permite_activos:
        estados_permitidos.add("activo")
    if permite_observacion:
        estados_permitidos.add("observacion")
    if permite_pasivos:
        estados_permitidos.add("pasivo")
    if permite_disciplina:
        estados_permitidos.add("disciplina")
    if permite_catecumenos:
        estados_permitidos.add("catecumeno")

    if estado_raw in estados_permitidos:
        return True

    if permite_nuevos and es_nuevo:
        return True

    if permite_menores and estado_raw == "":
        return True

    return False


def _get_rol_participacion_automatico(unidad, tenant):
    """
    Devuelve el rol de participación que debe usarse en la autoasignación.
    Si luego quieres uno específico por unidad, aquí es donde lo ajustamos.
    """
    return (
        RolUnidad.objects
        .filter(
            tenant=tenant,
            activo=True,
            tipo=RolUnidad.TIPO_PARTICIPACION,
        )
        .order_by("id")
        .first()
    )


def _sincronizar_membresias_automaticas(unidad, tenant):
    """
    Sincroniza automáticamente la membresía base de la unidad según sus reglas.
    NO toca liderazgo (UnidadCargo).
    """
    reglas = unidad.reglas or {}
    if not reglas.get("asignacion_automatica", False):
        return {
            "creados": 0,
            "reactivados": 0,
            "desactivados": 0,
            "sin_cambios": 0,
        }

    rol_participacion = _get_rol_participacion_automatico(unidad, tenant)
    if rol_participacion is None:
        return {
            "creados": 0,
            "reactivados": 0,
            "desactivados": 0,
            "sin_cambios": 0,
            "error": "No existe un rol activo de tipo PARTICIPACIÓN para la autoasignación.",
        }

    hoy = timezone.localdate()

    candidatos = Miembro.objects.filter(
        tenant=tenant,
        activo=True
    ).order_by("nombres", "apellidos")

    ids_elegibles = set()
    for miembro in candidatos:
        if _miembro_cumple_reglas_unidad_automatica(miembro, unidad):
            ids_elegibles.add(miembro.id)

    membresias_actuales = UnidadMembresia.objects.filter(tenant=tenant, unidad=unidad)

    creados = 0
    reactivados = 0
    desactivados = 0
    sin_cambios = 0

    existentes_por_miembro = {m.miembo_fk_id: m for m in membresias_actuales}

    for miembro_id in ids_elegibles:
        obj = existentes_por_miembro.get(miembro_id)

        if obj is None:
            UnidadMembresia.objects.create(
                tenant=tenant,
                unidad=unidad,
                miembo_fk_id=miembro_id,
                rol=rol_participacion,
                tipo="miembro",
                activo=True,
                fecha_ingreso=hoy,
                fecha_salida=None,
                notas="Asignación automática.",
            )
            creados += 1
        else:
            update_fields = []

            if obj.rol_id != rol_participacion.id:
                obj.rol = rol_participacion
                update_fields.append("rol")

            if not obj.activo:
                obj.activo = True
                update_fields.append("activo")
                reactivados += 1

            if obj.fecha_ingreso is None:
                obj.fecha_ingreso = hoy
                update_fields.append("fecha_ingreso")

            if obj.fecha_salida is not None:
                obj.fecha_salida = None
                update_fields.append("fecha_salida")

            nota_auto = "Asignación automática."
            notas_actuales = (obj.notas or "").strip()
            if nota_auto not in notas_actuales:
                obj.notas = (notas_actuales + "\n" + nota_auto).strip() if notas_actuales else nota_auto
                update_fields.append("notas")

            if update_fields:
                obj.save(update_fields=update_fields)
            else:
                sin_cambios += 1

    for obj in membresias_actuales:
        if obj.miembo_fk_id not in ids_elegibles and obj.activo:
            obj.activo = False
            obj.fecha_salida = hoy

            nota_salida = "Salida automática por reglas de unidad."
            notas_actuales = (obj.notas or "").strip()
            obj.notas = (notas_actuales + "\n" + nota_salida).strip() if notas_actuales else nota_salida

            obj.save(update_fields=["activo", "fecha_salida", "notas"])
            desactivados += 1

    return {
        "creados": creados,
        "reactivados": reactivados,
        "desactivados": desactivados,
        "sin_cambios": sin_cambios,
    }