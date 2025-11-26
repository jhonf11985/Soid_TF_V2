# core/utils_config.py
from django.conf import settings

from .models import ConfiguracionSistema


def get_config():
    """
    Devuelve la instancia única de configuración del sistema.
    Usamos el método load() que ya tienes definido en el modelo.
    """
    return ConfiguracionSistema.load()


def get_edad_minima_miembro_oficial():
    """
    Devuelve la edad mínima para considerar a alguien miembro oficial/bautizable.

    1) Primero lee el valor desde ConfiguracionSistema (campo edad_minima_miembro_oficial)
    2) Si no está definido, usa el valor por defecto de settings.EDAD_MINIMA_MIEMBRO_OFICIAL
    """
    cfg = get_config()

    # Si en la BD está vacío o es 0, usamos el valor de settings
    edad_cfg = getattr(cfg, "edad_minima_miembro_oficial", None)
    if not edad_cfg:
        return getattr(settings, "EDAD_MINIMA_MIEMBRO_OFICIAL", 12)

    return edad_cfg
