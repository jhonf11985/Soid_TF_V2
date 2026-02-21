from functools import wraps
from django.shortcuts import render


def evaluar_acceso_portal(user):

    # ----------------------------------
    # 1) Usuario sin miembro
    # ----------------------------------
    miembro = getattr(user, "miembro", None)
    if not miembro:
        return {
            "permitido": False,
            "tipo": "sin_vinculo",
            "titulo": "Cuenta no activada",
            "mensaje": "Tu cuenta aún no está vinculada al sistema de la iglesia. Contacta a secretaría para activarla.",
            "boton": "Contactar secretaría",
        }

    # ----------------------------------
    # 2) Nuevo creyente (NO entra)
    # ----------------------------------
    if getattr(miembro, "nuevo_creyente", False) or getattr(miembro, "etapa_actual", "") == "nuevo_creyente":
        return {
            "permitido": False,
            "tipo": "nuevo_creyente",
            "titulo": f"Hola {miembro.nombres}",
            "mensaje": (
                "Estamos felices de acompañarte en esta etapa.\n\n"
                "Tu acceso al portal se activará cuando completes tu proceso de seguimiento "
                "como Nuevo Creyente. Si necesitas ayuda, puedes escribirnos."
            ),
            "boton": "Contactar secretaría",
        }

    # ----------------------------------
    # Obtener estado desde razon_salida
    # ----------------------------------
    estado = getattr(miembro.razon_salida, "estado_resultante", None)

    # ----------------------------------
    # 3) Fallecido
    # ----------------------------------
    if estado == "fallecido":
        return {
            "permitido": False,
            "tipo": "fallecido",
            "titulo": f"En memoria de {miembro.nombres}",
            "mensaje": (
                "Este perfil ha sido cerrado.\n\n"
                "Damos gracias a Dios por su vida y el tiempo compartido con nosotros."
            ),
            "boton": None,
        }

    # ----------------------------------
    # 4) Trasladado
    # ----------------------------------
    if estado == "trasladado":
        return {
            "permitido": False,
            "tipo": "trasladado",
            "titulo": f"Hola {miembro.nombres}",
            "mensaje": (
                "Sabemos que ahora formas parte de otra congregación.\n\n"
                "Te bendecimos en esta nueva etapa. Tu acceso al portal ha sido cerrado "
                "para proteger tus datos."
            ),
            "boton": "Contactar secretaría",
        }

    # ----------------------------------
    # 5) Descarriado
    # ----------------------------------
    if estado == "descarriado":
        return {
            "permitido": False,
            "tipo": "descarriado",
            "titulo": f"Hola {miembro.nombres}",
            "mensaje": (
                "No es un adiós.\n\n"
                "Queremos que sepas que seguimos aquí para ti. "
                "Cuando desees volver a participar, estaremos dispuestos a acompañarte."
            ),
            "boton": "Hablar con un líder",
        }

    # ----------------------------------
    # 6) ACCESO PERMITIDO
    # ----------------------------------
    return {
        "permitido": True,
        "tipo": "normal",
    }


def acceso_portal_requerido(view_func):
    """
    Decorador que valida si el miembro tiene acceso al portal.
    Debe usarse DESPUÉS de @login_required.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        resultado = evaluar_acceso_portal(request.user)
        
        if not resultado["permitido"]:
            return render(request, "portal_miembros/acceso_restringido.html", resultado)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper