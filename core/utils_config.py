# core/utils_config.py
# ✅ CON SOPORTE MULTI-TENANT

from django.conf import settings
from .models import ConfiguracionSistema


def get_config(tenant):
    """
    Devuelve la instancia de configuración del tenant.
    
    Args:
        tenant: Instancia del modelo Tenant
    
    Returns:
        ConfiguracionSistema del tenant (o None si no hay tenant)
    """
    if not tenant:
        return None
    return ConfiguracionSistema.load(tenant)


def get_edad_minima_miembro_oficial(tenant=None):
    """
    Devuelve la edad mínima para considerar a alguien miembro oficial/bautizable.

    1) Si hay tenant, lee el valor desde ConfiguracionSistema
    2) Si no está definido o no hay tenant, usa el valor por defecto de settings
    
    Args:
        tenant: Instancia del modelo Tenant (opcional)
    """
    if tenant:
        cfg = get_config(tenant)
        if cfg:
            edad_cfg = getattr(cfg, "edad_minima_miembro_oficial", None)
            if edad_cfg:
                return edad_cfg
    
    # Fallback a settings
    return getattr(settings, "EDAD_MINIMA_MIEMBRO_OFICIAL", 12)