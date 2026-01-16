from .models import ConfiguracionSistema, Module

def configuracion_global(request):
    """
    Envía la configuración del sistema y los módulos activos
    a TODAS las plantillas.
    """
    config = ConfiguracionSistema.load()

    # Todos los módulos activos ordenados
    todos_los_modulos = list(Module.objects.filter(is_enabled=True).order_by('order', 'name'))
    
    # Diccionario para acceso rápido por código
    modulos_activos = {m.code: m for m in todos_los_modulos}
    
    # Para el bottom nav: primeros 3 son principales, el resto va en "Más"
    modulos_principales = todos_los_modulos[:3]
    modulos_extras = todos_los_modulos[3:]

    return {
        "CFG": config,
        "MODULOS_ACTIVOS": modulos_activos,
        "TODOS_LOS_MODULOS": todos_los_modulos,
        "MODULOS_PRINCIPALES": modulos_principales,
        "MODULOS_EXTRAS": modulos_extras,
    }