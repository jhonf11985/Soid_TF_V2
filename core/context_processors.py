from .models import ConfiguracionSistema, Module

def configuracion_global(request):
    """
    Envía la configuración del sistema y los módulos activos
    a TODAS las plantillas.
    """
    config = ConfiguracionSistema.load()

    modulos_activos = {
        m.code: m
        for m in Module.objects.filter(is_enabled=True)
    }

    return {
        "CFG": config,
        "MODULOS_ACTIVOS": modulos_activos,
    }
