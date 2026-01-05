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
    miembro = solicitud.miembro

    for f in EDITABLE_FIELDS:
        setattr(miembro, f, getattr(solicitud, f, ""))

    miembro.save(update_fields=EDITABLE_FIELDS)
    return miembro
