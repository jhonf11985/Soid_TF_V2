from miembros_app.models import Miembro
from .models import SolicitudActualizacionMiembro


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
