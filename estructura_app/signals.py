from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from miembros_app.models import Miembro
from estructura_app.models import Unidad, UnidadMembresia, RolUnidad


def _get_edad_value(miembro):
    """
    Devuelve la edad como entero si existe.
    Soporta:
    - miembro.edad
    - miembro.fecha_nacimiento
    """
    if hasattr(miembro, "edad") and miembro.edad is not None:
        try:
            return int(miembro.edad)
        except Exception:
            pass

    if hasattr(miembro, "fecha_nacimiento") and miembro.fecha_nacimiento:
        hoy = timezone.localdate()
        fn = miembro.fecha_nacimiento
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))

    return None


def _cumple_rango_edad(miembro, unidad):
    edad_min = getattr(unidad, "edad_min", None)
    edad_max = getattr(unidad, "edad_max", None)

    if edad_min is None and edad_max is None:
        return True

    edad = _get_edad_value(miembro)
    if edad is None:
        return True

    if edad_min is not None and edad < edad_min:
        return False

    if edad_max is not None and edad > edad_max:
        return False

    return True


def _miembro_cumple_reglas_unidad_automatica(miembro, unidad):
    reglas = unidad.reglas or {}

    if not reglas.get("asignacion_automatica", False):
        return False

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
    if solo_activos:
        return estado_raw == "activo"

    estados_permitidos = {"activo"}

    if reglas.get("permite_observacion"):
        estados_permitidos.add("observacion")
    if reglas.get("permite_pasivos"):
        estados_permitidos.add("pasivo")
    if reglas.get("permite_disciplina"):
        estados_permitidos.add("disciplina")
    if reglas.get("permite_catecumenos"):
        estados_permitidos.add("catecumeno")

    if estado_raw in estados_permitidos:
        return True

    if reglas.get("permite_nuevos") and es_nuevo:
        return True

    if reglas.get("permite_menores") and estado_raw == "":
        return True

    return False


def _obtener_rol_participacion(tenant):
    """
    Obtiene el único rol de tipo PARTICIPACIÓN del tenant.
    Retorna None si no existe.
    """
    return RolUnidad.objects.filter(
        tenant=tenant,
        tipo=RolUnidad.TIPO_PARTICIPACION,
        activo=True,
    ).first()


def _sincronizar_miembro_en_unidades_automaticas(miembro):
    """
    Evalúa un solo miembro contra todas las unidades automáticas
    DEL MISMO TENANT.
    
    REGLA CLAVE: Si la membresía ya tiene un rol asignado, NO SE TOCA.
    Solo se asigna rol cuando se crea nueva membresía o cuando rol=None.
    """
    tenant = getattr(miembro, "tenant", None)
    if tenant is None:
        return

    hoy = timezone.localdate()

    # Obtener el rol de participación una sola vez
    rol_participacion = _obtener_rol_participacion(tenant)

    unidades = Unidad.objects.filter(
        tenant=tenant,
        activa=True,
        reglas__asignacion_automatica=True,
    )

    for unidad in unidades:
        debe_estar = _miembro_cumple_reglas_unidad_automatica(miembro, unidad)

        # Buscar membresía existente CON el rol cargado
        membresia = UnidadMembresia.objects.select_related("rol").filter(
            tenant=tenant,
            unidad=unidad,
            miembo_fk=miembro,
        ).first()

        if debe_estar:
            if membresia is None:
                # CASO 1: No existe membresía → Crear con rol PARTICIPACIÓN
                UnidadMembresia.objects.create(
                    tenant=tenant,
                    unidad=unidad,
                    miembo_fk=miembro,
                    rol=rol_participacion,
                    tipo="miembro",
                    activo=True,
                    fecha_ingreso=hoy,
                    fecha_salida=None,
                    notas="Asignación automática.",
                )
            else:
                # CASO 2: Ya existe membresía → Solo reactivar si es necesario
                # NUNCA tocar el rol si ya tiene uno asignado
                cambios = []

                # Si no tiene rol, asignar PARTICIPACIÓN
                if membresia.rol_id is None and rol_participacion:
                    membresia.rol = rol_participacion
                    cambios.append("rol")

                # Reactivar si estaba inactivo
                if not membresia.activo:
                    membresia.activo = True
                    cambios.append("activo")

                if membresia.fecha_ingreso is None:
                    membresia.fecha_ingreso = hoy
                    cambios.append("fecha_ingreso")

                if membresia.fecha_salida is not None:
                    membresia.fecha_salida = None
                    cambios.append("fecha_salida")

                if cambios:
                    membresia.save(update_fields=cambios)

        else:
            # El miembro NO debe estar en esta unidad
            if membresia and membresia.activo:
                # Determinar el tipo de rol actual
                rol_tipo = None
                if membresia.rol is not None:
                    rol_tipo = getattr(membresia.rol, "tipo", None)

                # Solo desactivar si el rol es PARTICIPACIÓN o None
                # Los roles de TRABAJO NO se tocan (asignados manualmente)
                if rol_tipo is None or rol_tipo == RolUnidad.TIPO_PARTICIPACION:
                    nota_salida = "Salida automática por reglas de unidad."
                    notas_actuales = (membresia.notas or "").strip()
                    membresia.notas = (notas_actuales + "\n" + nota_salida).strip() if notas_actuales else nota_salida
                    membresia.activo = False
                    membresia.fecha_salida = hoy
                    membresia.save(update_fields=["activo", "fecha_salida", "notas"])
                # Si es TRABAJO, no se hace nada - se mantiene activo


@receiver(post_save, sender=Miembro)
def autoasignar_miembro_en_unidades(sender, instance, **kwargs):
    _sincronizar_miembro_en_unidades_automaticas(instance)