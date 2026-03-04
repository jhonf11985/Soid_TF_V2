import re
from django.db import transaction
from miembros_app.models import Miembro, MiembroRelacion, sync_familia_inteligente_por_relacion
from .models import SolicitudActualizacionMiembro, SolicitudAltaMiembro, AccesoActualizacionDatos


EDITABLE_FIELDS = [
    "telefono", "whatsapp", "email",
    "direccion", "sector", "ciudad", "provincia", "codigo_postal",
    "empleador", "puesto", "telefono_trabajo", "direccion_trabajo",
    "contacto_emergencia_nombre", "contacto_emergencia_telefono", "contacto_emergencia_relacion",
    "tipo_sangre", "alergias", "condiciones_medicas", "medicamentos",
]


def aplicar_solicitud_a_miembro(solicitud: SolicitudActualizacionMiembro) -> Miembro:
    """
    Aplica al Miembro SOLO los campos que vengan con valor en la solicitud.
    """
    miembro = solicitud.miembro
    campos_a_guardar = []

    for f in EDITABLE_FIELDS:
        valor = getattr(solicitud, f, None)

        if isinstance(valor, str):
            valor = valor.strip()

        if valor in ("", None):
            continue

        actual = getattr(miembro, f, None)
        if isinstance(actual, str):
            actual = actual.strip()

        if valor == actual:
            continue

        setattr(miembro, f, valor)
        campos_a_guardar.append(f)

    if campos_a_guardar:
        miembro.save(update_fields=campos_a_guardar)

    return miembro


def _normalizar_cedula_rd(valor: str) -> str:
    """
    Convierte cédula a formato 000-0000000-0 si vienen 11 dígitos.
    """
    if not valor:
        return ""
    d = re.sub(r"\D", "", (valor or "").strip())
    if len(d) == 11:
        return f"{d[:3]}-{d[3:10]}-{d[10]}"
    return (valor or "").strip()


def crear_miembro_desde_solicitud_alta(solicitud: SolicitudAltaMiembro) -> Miembro:
    """
    Convierte una SolicitudAltaMiembro (pendiente) en un Miembro real.
    """
    tenant = solicitud.tenant
    tel = (solicitud.telefono or "").strip()
    ced = _normalizar_cedula_rd(solicitud.cedula or "")

    # Duplicados (filtrar por tenant)
    if tel and Miembro.objects.filter(tenant=tenant, telefono=tel).exists():
        raise ValueError(f"Ya existe un miembro con el teléfono {tel}.")

    if ced and Miembro.objects.filter(tenant=tenant, cedula=ced).exists():
        raise ValueError(f"Ya existe un miembro con la cédula {ced}.")

    with transaction.atomic():
        miembro = Miembro.objects.create(
            tenant=tenant,  # <-- TENANT
            nombres=(solicitud.nombres or "").strip(),
            apellidos=(solicitud.apellidos or "").strip(),
            genero=solicitud.genero,
            fecha_nacimiento=solicitud.fecha_nacimiento,
            fecha_ingreso_iglesia=solicitud.fecha_ingreso_iglesia,
            estado_miembro=solicitud.estado_miembro,
            telefono=tel,
            whatsapp=(solicitud.whatsapp or "").strip(),
            direccion=(solicitud.direccion or "").strip(),
            sector=(solicitud.sector or "").strip(),
            ciudad=solicitud.ciudad or "Higuey",
            provincia="La Altagracia",
            cedula=ced or None,
            foto=solicitud.foto if getattr(solicitud, "foto", None) else None,
            bautizado_confirmado=(solicitud.estado_miembro != "catecumeno"),
        )

        acceso, _ = AccesoActualizacionDatos.objects.get_or_create(
            miembro=miembro,
            defaults={"tenant": tenant}
        )
        if not acceso.activo:
            acceso.activo = True
            acceso.save(update_fields=["activo", "actualizado_en"])

    return miembro


# ==========================================================
# FAMILIA
# ==========================================================

def _ya_tiene_conyuge(miembro: Miembro):
    return MiembroRelacion.objects.filter(miembro=miembro, tipo_relacion="conyuge").values_list("familiar_id", flat=True)


def _ya_tiene_padre(miembro: Miembro):
    return MiembroRelacion.objects.filter(miembro=miembro, tipo_relacion="padre").values_list("familiar_id", flat=True)


def _ya_tiene_madre(miembro: Miembro):
    return MiembroRelacion.objects.filter(miembro=miembro, tipo_relacion="madre").values_list("familiar_id", flat=True)


@transaction.atomic
def _crear_relacion_segura(*, miembro: Miembro, familiar: Miembro, tipo: str, alertas: list, creadas: list):
    if miembro.id == familiar.id:
        alertas.append({"tipo": tipo, "motivo": "self", "detalle": "No se puede relacionar un miembro consigo mismo."})
        return

    if tipo == "conyuge":
        actuales = set(_ya_tiene_conyuge(miembro))
        actuales |= set(_ya_tiene_conyuge(familiar))
        if actuales and (familiar.id not in actuales or miembro.id not in actuales):
            alertas.append({
                "tipo": "conyuge",
                "motivo": "conflicto",
                "detalle": f"Choque: ya existe cónyuge registrado (miembro {miembro.id} o {familiar.id}). No se creó.",
            })
            return

    if tipo == "padre":
        actuales = list(_ya_tiene_padre(miembro))
        if actuales and familiar.id not in actuales:
            alertas.append({
                "tipo": "padre",
                "motivo": "conflicto",
                "detalle": f"El miembro {miembro.id} ya tiene padre registrado ({actuales[0]}). No se creó otro.",
            })
            return

    if tipo == "madre":
        actuales = list(_ya_tiene_madre(miembro))
        if actuales and familiar.id not in actuales:
            alertas.append({
                "tipo": "madre",
                "motivo": "conflicto",
                "detalle": f"El miembro {miembro.id} ya tiene madre registrada ({actuales[0]}). No se creó otra.",
            })
            return

    rel, created = MiembroRelacion.objects.get_or_create(
        miembro=miembro,
        familiar=familiar,
        tipo_relacion=tipo,
        defaults={"vive_junto": True},
    )
    if created:
        creadas.append({"tipo": tipo, "miembro_id": miembro.id, "familiar_id": familiar.id})
        sync_familia_inteligente_por_relacion(rel)

    inv_tipo = MiembroRelacion.inverse_tipo(tipo, miembro.genero)
    inv, inv_created = MiembroRelacion.objects.get_or_create(
        miembro=familiar,
        familiar=miembro,
        tipo_relacion=inv_tipo,
        defaults={"vive_junto": True},
    )
    if inv_created:
        creadas.append({"tipo": inv_tipo, "miembro_id": familiar.id, "familiar_id": miembro.id})
        sync_familia_inteligente_por_relacion(inv)


@transaction.atomic
def aplicar_alta_familia(*, jefe_id: int, conyuge_id=None, padre_id=None, madre_id=None, hijos_ids=None):
    """
    Crea relaciones directas: conyuge, padre, madre, hijos.
    """
    hijos_ids = hijos_ids or []

    jefe = Miembro.objects.get(id=jefe_id)
    alertas = []
    creadas = []

    if conyuge_id:
        cony = Miembro.objects.get(id=conyuge_id)
        _crear_relacion_segura(miembro=jefe, familiar=cony, tipo="conyuge", alertas=alertas, creadas=creadas)

    if padre_id:
        padre = Miembro.objects.get(id=padre_id)
        _crear_relacion_segura(miembro=jefe, familiar=padre, tipo="padre", alertas=alertas, creadas=creadas)

    if madre_id:
        madre = Miembro.objects.get(id=madre_id)
        _crear_relacion_segura(miembro=jefe, familiar=madre, tipo="madre", alertas=alertas, creadas=creadas)

    for hid in hijos_ids:
        if not hid:
            continue
        hijo = Miembro.objects.get(id=int(hid))
        _crear_relacion_segura(miembro=jefe, familiar=hijo, tipo="hijo", alertas=alertas, creadas=creadas)

    return {"creadas": creadas, "alertas": alertas}