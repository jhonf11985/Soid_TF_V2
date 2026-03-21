# estructura_app/view_helpers/visitas_unidad.py
"""
Helpers para determinar qué visitas corresponden a una unidad
según sus reglas de edad y género.
"""

from datetime import date


def _get_edad_visita(visita):
    """
    Obtiene la edad de una visita.
    Primero intenta el campo 'edad', si no existe o es None,
    intenta calcular desde fecha_nacimiento si existe.
    """
    # Campo directo
    if hasattr(visita, "edad") and visita.edad is not None:
        try:
            return int(visita.edad)
        except (ValueError, TypeError):
            pass

    # Calcular desde fecha_nacimiento si existe
    if hasattr(visita, "fecha_nacimiento") and visita.fecha_nacimiento:
        hoy = date.today()
        fn = visita.fecha_nacimiento
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))

    return None


def _get_genero_visita(visita):
    """
    Devuelve 'M' o 'F' normalizado, o None si no tiene género.
    """
    genero = getattr(visita, "genero", None)
    if not genero:
        return None

    g = str(genero).strip().upper()
    if g in ("M", "MASCULINO", "HOMBRE"):
        return "M"
    if g in ("F", "FEMENINO", "MUJER"):
        return "F"
    return None


def visita_cumple_reglas_unidad(visita, unidad):
    """
    Evalúa si una visita cumple con las reglas de edad y género de una unidad.
    
    Retorna True si:
    - La edad está dentro del rango [edad_min, edad_max] de la unidad
    - El género es admitido (admite_hombres / admite_mujeres)
    
    Si la unidad no tiene restricciones definidas, retorna False
    (para evitar que todas las visitas aparezcan en todas las unidades).
    """
    reglas = unidad.reglas or {}
    
    # Verificar si la unidad tiene restricciones de edad/género definidas
    edad_min = getattr(unidad, "edad_min", None)
    edad_max = getattr(unidad, "edad_max", None)
    admite_hombres = reglas.get("admite_hombres", False)
    admite_mujeres = reglas.get("admite_mujeres", False)
    
    # Si no hay ninguna restricción definida, no mostrar visitas
    # (evita que una unidad sin reglas muestre todas las visitas)
    if edad_min is None and edad_max is None and not admite_hombres and not admite_mujeres:
        return False
    
    # Si no admite ningún género, no puede cumplir
    if not admite_hombres and not admite_mujeres:
        return False
    
    # ══════════════════════════════════════════
    # EVALUACIÓN DE GÉNERO
    # ══════════════════════════════════════════
    genero_visita = _get_genero_visita(visita)
    
    if genero_visita:
        if genero_visita == "M" and not admite_hombres:
            return False
        if genero_visita == "F" and not admite_mujeres:
            return False
    else:
        # Si la visita no tiene género y la unidad tiene restricción de género,
        # no podemos determinar si cumple
        if admite_hombres != admite_mujeres:
            # La unidad tiene restricción (solo uno de los dos)
            return False
    
    # ══════════════════════════════════════════
    # EVALUACIÓN DE EDAD
    # ══════════════════════════════════════════
    if edad_min is not None or edad_max is not None:
        edad_visita = _get_edad_visita(visita)
        
        if edad_visita is None:
            # Si la unidad requiere rango de edad pero la visita no tiene edad,
            # no podemos determinar si cumple
            return False
        
        if edad_min is not None and edad_visita < edad_min:
            return False
        if edad_max is not None and edad_visita > edad_max:
            return False
    
    return True


def get_visitas_para_unidad(unidad, tenant):
    """
    Obtiene todas las visitas que cumplen con las reglas de la unidad.
    
    Retorna un QuerySet filtrado de visitas.
    """
    from visitas_app.models import Visita
    
    reglas = unidad.reglas or {}
    
    # Si no permite visitas, retornar queryset vacío
    if not reglas.get("permite_visitas", False):
        return Visita.objects.none()
    
    # Obtener parámetros de filtro
    edad_min = getattr(unidad, "edad_min", None)
    edad_max = getattr(unidad, "edad_max", None)
    admite_hombres = reglas.get("admite_hombres", False)
    admite_mujeres = reglas.get("admite_mujeres", False)
    
    # Si no hay restricciones definidas, no mostrar visitas
    if edad_min is None and edad_max is None and not admite_hombres and not admite_mujeres:
        return Visita.objects.none()
    
    # Base queryset
    visitas_qs = (
        Visita.objects
        .filter(tenant=tenant)
        .select_related("registro", "registro__tipo", "clasificacion")
        .order_by("-fecha_ultima_visita", "-id")
    )
    
    # ══════════════════════════════════════════
    # FILTRO DE GÉNERO (a nivel de DB)
    # ══════════════════════════════════════════
    if admite_hombres and not admite_mujeres:
        visitas_qs = visitas_qs.filter(genero="M")
    elif admite_mujeres and not admite_hombres:
        visitas_qs = visitas_qs.filter(genero="F")
    elif not admite_hombres and not admite_mujeres:
        return Visita.objects.none()
    # Si admite ambos, no filtrar por género
    
    # ══════════════════════════════════════════
    # FILTRO DE EDAD (a nivel de DB)
    # ══════════════════════════════════════════
    if edad_min is not None:
        visitas_qs = visitas_qs.filter(edad__gte=edad_min)
    if edad_max is not None:
        visitas_qs = visitas_qs.filter(edad__lte=edad_max)
    
    return visitas_qs


def get_resumen_visitas_unidad(visitas_qs):
    """
    Genera un resumen estadístico de las visitas.
    """
    total = visitas_qs.count()
    primera_vez = visitas_qs.filter(primera_vez=True).count()
    recurrentes = total - primera_vez
    
    # Por género
    masculinos = visitas_qs.filter(genero="M").count()
    femeninos = visitas_qs.filter(genero="F").count()
    
    return {
        "total": total,
        "primera_vez": primera_vez,
        "recurrentes": recurrentes,
        "masculinos": masculinos,
        "femeninos": femeninos,
    }