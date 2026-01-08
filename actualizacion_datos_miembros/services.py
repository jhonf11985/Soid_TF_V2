import re
from django.db import transaction
from miembros_app.models import Miembro
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
    - Evita que campos vacíos ("") borren datos existentes.
    - Guarda únicamente los campos realmente modificados.
    """
    miembro = solicitud.miembro
    campos_a_guardar = []

    for f in EDITABLE_FIELDS:
        valor = getattr(solicitud, f, None)

        # Si es string, lo limpiamos (sin obligar a que tenga contenido)
        if isinstance(valor, str):
            valor = valor.strip()

        # Si viene vacío o None, no tocar el dato actual
        if valor in ("", None):
            continue

        # Si el valor es igual al actual, no hace falta guardar
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
    Si viene vacía, devuelve "".
    """
    if not valor:
        return ""
    d = re.sub(r"\D", "", (valor or "").strip())
    if len(d) == 11:
        return f"{d[:3]}-{d[3:10]}-{d[10]}"
    # Si no son 11 dígitos, devolvemos lo que venga (limpio) para no inventar
    return (valor or "").strip()


def crear_miembro_desde_solicitud_alta(solicitud: SolicitudAltaMiembro) -> Miembro:
    """
    Convierte una SolicitudAltaMiembro (pendiente) en un Miembro real.

    - Valida duplicados por teléfono y por cédula (si viene).
    - Copia foto y datos básicos.
    - Crea/activa automáticamente el AccesoActualizacionDatos.
    """
    tel = (solicitud.telefono or "").strip()
    ced = _normalizar_cedula_rd(solicitud.cedula or "")

    # Duplicados
    if tel and Miembro.objects.filter(telefono=tel).exists():
        raise ValueError(f"Ya existe un miembro con el teléfono {tel}.")

    if ced and Miembro.objects.filter(cedula=ced).exists():
        raise ValueError(f"Ya existe un miembro con la cédula {ced}.")

    with transaction.atomic():
        miembro = Miembro.objects.create(
            nombres=(solicitud.nombres or "").strip(),
            apellidos=(solicitud.apellidos or "").strip(),
            genero=solicitud.genero,
            fecha_nacimiento=solicitud.fecha_nacimiento,
            estado_miembro=solicitud.estado_miembro,
            telefono=tel,
            whatsapp=(solicitud.whatsapp or "").strip(),
            direccion=(solicitud.direccion or "").strip(),
            sector=(solicitud.sector or "").strip(),
            cedula=ced or None,
            foto=solicitud.foto if getattr(solicitud, "foto", None) else None,

             bautizado_confirmado=(solicitud.estado_miembro != "catecumeno"),

        )

        acceso, _ = AccesoActualizacionDatos.objects.get_or_create(miembro=miembro)
        if not acceso.activo:
            acceso.activo = True
            acceso.save(update_fields=["activo", "actualizado_en"])

    return miembro
