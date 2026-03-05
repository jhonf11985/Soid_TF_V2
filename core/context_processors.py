# context_processors.py
# Actualizado con sistema de mensajes inteligentes de bienvenida
# ✅ CON SOPORTE MULTI-TENANT

from django.conf import settings
from django.apps import apps
from .models import ConfiguracionSistema, Module


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def configuracion_global(request):
    """
    Envía la configuración del sistema, módulos activos
    y contexto inteligente de SOID a TODAS las plantillas.
    """
    # ✅ OBTENER TENANT (puede ser None en admin/login)
    tenant = getattr(request, 'tenant', None)
    
    # ✅ CARGAR CONFIG SOLO SI HAY TENANT
    if tenant:
        config = ConfiguracionSistema.load(tenant)
    else:
        config = None

    # Todos los módulos activos ordenados
    todos_los_modulos = list(Module.objects.filter(is_enabled=True).order_by('order', 'name'))
    
    # Diccionario para acceso rápido por código
    modulos_activos = {m.code: m for m in todos_los_modulos}
    
    # Para el bottom nav: primeros 3 son principales, el resto va en "Más"
    modulos_principales = todos_los_modulos[:3]
    modulos_extras = todos_los_modulos[3:]

    # ===============================
    # 🧠 CONTEXTO INTELIGENTE DE SOID
    # ===============================
    soid_ctx = {
        "tiene_miembro": False,
        "rol": "usuario",
        "pendientes": {
            "pendiente_envio_nuevo_creyente": 0,
            "sin_padre_espiritual": 0,
        },
    }

    u = getattr(request, "user", None)

    if u and getattr(u, "is_authenticated", False):

        # 1) ¿Tiene miembro vinculado?
        try:
            soid_ctx["tiene_miembro"] = bool(getattr(u, "miembro", None))
        except Exception:
            soid_ctx["tiene_miembro"] = False

        # 2) Rol del usuario
        if getattr(u, "is_superuser", False):
            soid_ctx["rol"] = "admin"
        else:
            try:
                groups = [g.name.lower() for g in u.groups.all()]
            except Exception:
                groups = []

            if any("admin" in g or "geren" in g for g in groups):
                soid_ctx["rol"] = "admin"
            elif any("secre" in g for g in groups):
                soid_ctx["rol"] = "secretaria"
            elif any("lider" in g or "pastor" in g for g in groups):
                soid_ctx["rol"] = "lider"
            else:
                soid_ctx["rol"] = "usuario"

        # 3) Pendientes del sistema (Miembros) - SOLO SI HAY TENANT
        if tenant:
            try:
                Miembro = apps.get_model("miembros_app", "Miembro")
            except Exception:
                Miembro = None

            if Miembro:
                # ✅ FILTRAR POR TENANT
                base_qs = Miembro.objects.filter(tenant=tenant)
                
                # Miembros sin padre espiritual
                for f in ["padre_espiritual", "padre_espiritual_miembro", "padre_espiritual_fk"]:
                    if _has_field(Miembro, f):
                        soid_ctx["pendientes"]["sin_padre_espiritual"] = base_qs.filter(**{f"{f}__isnull": True}).count()
                        break

                # Pendientes de envío a Nuevo Creyente
                for f in [
                    "pendiente_envio_nuevo_creyente",
                    "pendiente_envio_nc",
                    "pendiente_envio",
                    "nuevo_creyente_pendiente_envio",
                    "pendiente_a_nuevo_creyente",
                ]:
                    if _has_field(Miembro, f):
                        soid_ctx["pendientes"]["pendiente_envio_nuevo_creyente"] = base_qs.filter(**{f: True}).count()
                        break

    # ===============================
    # 💬 MENSAJE DE BIENVENIDA
    # ===============================
    welcome_message = None
    if hasattr(request, 'session'):
        welcome_message = request.session.pop('welcome_message', None)

    return {
        "CFG": config,
        "MODULOS_ACTIVOS": modulos_activos,
        "TODOS_LOS_MODULOS": todos_los_modulos,
        "MODULOS_PRINCIPALES": modulos_principales,
        "MODULOS_EXTRAS": modulos_extras,
        "VAPID_PUBLIC_KEY": getattr(settings, 'VAPID_PUBLIC_KEY', ''),

        # 🧠 SOID INTELIGENTE
        "SOID_CTX": soid_ctx,
        
        # 💬 MENSAJE DE BIENVENIDA
        "WELCOME_MESSAGE": welcome_message,
    }