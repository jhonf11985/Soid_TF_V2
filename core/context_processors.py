from .models import ConfiguracionSistema

def configuracion_global(request):
    """
    Envía la configuración del sistema a TODAS las plantillas.
    """
    config = ConfiguracionSistema.load()
    return {
        "CFG": config
    }
