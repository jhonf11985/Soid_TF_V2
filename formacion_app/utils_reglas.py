# formacion_app/utils_reglas.py
from __future__ import annotations

from datetime import date, timedelta
from miembros_app.models import Miembro


def _safe_replace_year(d: date, year: int) -> date:
    """Cambia el año manteniendo mes/día. Si es 29-Feb en año no bisiesto, cae a 28-Feb."""
    try:
        return d.replace(year=year)
    except ValueError:
        return d.replace(year=year, day=28)


def rango_nacimiento_por_edad(edad_min: int | None, edad_max: int | None, hoy: date | None = None):
    """
    Devuelve (nac_min, nac_max) inclusivos para filtrar por fecha_nacimiento.

    - edad >= X  -> nacimiento <= hoy - X años  (nac_max)
    - edad <= Y  -> nacimiento >= (hoy - (Y+1) años) + 1 día  (nac_min)
    """
    if hoy is None:
        hoy = date.today()

    nac_max = None
    nac_min = None

    if edad_min is not None:
        nac_max = _safe_replace_year(hoy, hoy.year - int(edad_min))

    if edad_max is not None:
        limite = _safe_replace_year(hoy, hoy.year - (int(edad_max) + 1)) + timedelta(days=1)
        nac_min = limite

    return nac_min, nac_max


def miembros_elegibles_por_grupo(grupo, hoy: date | None = None):
    """
    SUGERENCIA (no bloquea):
    Devuelve miembros que 'deberían' estar según reglas del grupo:
    - sexo_permitido (VARONES/HEMBRAS/MIXTO)
    - edad_min / edad_max
    """
    if hoy is None:
        hoy = date.today()

    qs = Miembro.objects.all()

    # Base: si existe 'estado_miembro', excluimos INACTIVO; si existe 'activo', filtramos activo=True
    try:
        Miembro._meta.get_field("estado_miembro")
        qs = qs.exclude(estado_miembro="INACTIVO")
    except Exception:
        try:
            Miembro._meta.get_field("activo")
            qs = qs.filter(activo=True)
        except Exception:
            pass

    # Sexo
    try:
        Miembro._meta.get_field("genero")
        if getattr(grupo, "sexo_permitido", "MIXTO") == "VARONES":
            qs = qs.filter(genero="masculino")
        elif getattr(grupo, "sexo_permitido", "MIXTO") == "HEMBRAS":
            qs = qs.filter(genero="femenino")
    except Exception:
        pass

    # Edad (por fecha_nacimiento)
    try:
        Miembro._meta.get_field("fecha_nacimiento")
        qs = qs.exclude(fecha_nacimiento__isnull=True)

        nac_min, nac_max = rango_nacimiento_por_edad(
            getattr(grupo, "edad_min", None),
            getattr(grupo, "edad_max", None),
            hoy=hoy
        )

        if nac_min is not None:
            qs = qs.filter(fecha_nacimiento__gte=nac_min)
        if nac_max is not None:
            qs = qs.filter(fecha_nacimiento__lte=nac_max)
    except Exception:
        pass

    return qs.order_by("nombres", "apellidos")


def reporte_reglas_grupo(grupo, hoy: date | None = None):
    """
    Retorna:
      - elegibles: miembros que deberían estar (según reglas)
      - inscritos: miembros inscritos actualmente (estado ACTIVO)
      - faltan: elegibles que no están inscritos
      - sobran: inscritos que no son elegibles
    """
    elegibles = miembros_elegibles_por_grupo(grupo, hoy=hoy)

    inscritos_ids = grupo.inscripciones.filter(estado="ACTIVO").values_list("miembro_id", flat=True)
    inscritos = Miembro.objects.filter(id__in=inscritos_ids).order_by("nombres", "apellidos")

    elegibles_ids = elegibles.values_list("id", flat=True)

    faltan = elegibles.exclude(id__in=inscritos_ids)
    sobran = inscritos.exclude(id__in=elegibles_ids)

    return {
        "elegibles": elegibles,
        "inscritos": inscritos,
        "faltan": faltan,
        "sobran": sobran,
    }
