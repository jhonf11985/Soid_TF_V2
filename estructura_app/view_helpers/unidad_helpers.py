from datetime import date


def _to_int_from_post(post, name, default=None):
    raw = (post.get(name) or "").strip()
    if raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _to_int_or_none(value):
    if value is None:
        return None
    try:
        s = str(value).strip()
        if s == "":
            return None
        return int(s)
    except Exception:
        return None


def _get_edad_value(miembro):
    """
    Devuelve la edad como entero si existe.
    """
    if hasattr(miembro, "edad") and miembro.edad is not None:
        try:
            return int(miembro.edad)
        except Exception:
            pass

    if hasattr(miembro, "fecha_nacimiento") and miembro.fecha_nacimiento:
        hoy = date.today()
        fn = miembro.fecha_nacimiento
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))

    return None


def _cumple_rango_edad(miembro, unidad):
    """
    True si el miembro está dentro del rango edad_min/edad_max de la unidad.
    """
    edad_min = getattr(unidad, "edad_min", None)
    edad_max = getattr(unidad, "edad_max", None)

    if edad_min is None and edad_max is None:
        return True

    edad = _get_edad_value(miembro)
    if edad is None:
        return True

    if edad_min is not None and edad < edad_min:
        return False
    if edad_max is not None and edad > edad_max:
        return False

    return True


def _cumple_rango_edad_liderazgo(miembro, reglas):
    """
    Evalúa el rango de liderazgo usando reglas["lider_edad_min/max"].
    """
    edad_min = _to_int_or_none(reglas.get("lider_edad_min"))
    edad_max = _to_int_or_none(reglas.get("lider_edad_max"))

    if edad_min is None and edad_max is None:
        return True

    edad = _get_edad_value(miembro)
    if edad is None:
        return True

    if edad_min is not None and edad < edad_min:
        return False
    if edad_max is not None and edad > edad_max:
        return False

    return True


def _estado_slug(estado):
    if not estado:
        return "vacio"

    s = str(estado).strip().lower()
    s = (
        s.replace("á", "a")
         .replace("é", "e")
         .replace("í", "i")
         .replace("ó", "o")
         .replace("ú", "u")
         .replace("ñ", "n")
    )
    return s


def _genero_label(miembro):
    """
    Devuelve 'Hombre' / 'Mujer' / '—' de forma robusta.
    """
    try:
        label = (miembro.get_genero_display() or "").strip()
        if label:
            return label
    except Exception:
        pass

    raw = (getattr(miembro, "genero", "") or "").strip().lower()
    if raw in ("m", "masculino", "hombre"):
        return "Hombre"
    if raw in ("f", "femenino", "mujer"):
        return "Mujer"
    return "—"


def _reglas_mvp_from_post(post, base_reglas=None):
    """
    Lee reglas MVP desde request.POST y devuelve un dict listo para guardar.
    """
    base_reglas = base_reglas or {}

    def to_int(name, default=None):
        raw = (post.get(name) or "").strip()
        if raw == "":
            key = name.replace("regla_", "")
            if key in base_reglas and base_reglas.get(key) is not None:
                return base_reglas.get(key)
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    asignacion_automatica = post.get("regla_asignacion_automatica") in ("on", "1", "true", "True")
    solo_activos = post.get("regla_solo_activos") in ("on", "1", "true", "True")
    permite_activos = True if solo_activos else post.get("regla_perm_activos") in ("on", "1", "true", "True")

    admite_hombres = post.get("regla_admite_hombres") in ("on", "1", "true", "True")
    admite_mujeres = post.get("regla_admite_mujeres") in ("on", "1", "true", "True")
    permite_liderazgo = post.get("regla_perm_liderazgo") in ("on", "1", "true", "True")
    permite_subunidades = post.get("regla_perm_subunidades") in ("on", "1", "true", "True")
    requiere_aprobacion = post.get("regla_req_aprob_lider") in ("on", "1", "true", "True")
    unidad_privada = post.get("regla_unidad_privada") in ("on", "1", "true", "True")

    permite_observacion = False if solo_activos else post.get("regla_perm_observacion") in ("on", "1", "true", "True")
    permite_pasivos = False if solo_activos else post.get("regla_perm_pasivos") in ("on", "1", "true", "True")
    permite_disciplina = False if solo_activos else post.get("regla_perm_disciplina") in ("on", "1", "true", "True")
    permite_catecumenos = False if solo_activos else post.get("regla_perm_catecumenos") in ("on", "1", "true", "True")
    permite_nuevos = False if solo_activos else post.get("regla_perm_nuevos") in ("on", "1", "true", "True")
    permite_menores = False if solo_activos else post.get("regla_perm_menores") in ("on", "1", "true", "True")
    
    # ═══════════════════════════════════════════════════════════════
    # REGLA: permite_visitas
    # ═══════════════════════════════════════════════════════════════
    permite_visitas = post.get("regla_perm_visitas") in ("on", "1", "true", "True")

    # ═══════════════════════════════════════════════════════════════
    # PESTAÑAS VISIBLES
    # ═══════════════════════════════════════════════════════════════
    pestana_liderazgo = post.get("pestana_liderazgo") in ("on", "1", "true", "True")
    pestana_equipo_trabajo = post.get("pestana_equipo_trabajo") in ("on", "1", "true", "True")
    pestana_actividades = post.get("pestana_actividades") in ("on", "1", "true", "True")
    pestana_finanzas = post.get("pestana_finanzas") in ("on", "1", "true", "True")
    pestana_reportes = post.get("pestana_reportes") in ("on", "1", "true", "True")

    return {
        "asignacion_automatica": asignacion_automatica,
        "solo_activos": solo_activos,
        "permite_activos": permite_activos,
        "admite_hombres": admite_hombres,
        "admite_mujeres": admite_mujeres,
        "permite_observacion": permite_observacion,
        "permite_pasivos": permite_pasivos,
        "permite_disciplina": permite_disciplina,
        "permite_catecumenos": permite_catecumenos,
        "permite_nuevos": permite_nuevos,
        "permite_menores": permite_menores,
        "permite_visitas": permite_visitas,
        "lider_edad_min": to_int("regla_lider_edad_min"),
        "lider_edad_max": to_int("regla_lider_edad_max"),
        "permite_liderazgo": permite_liderazgo,
        "limite_lideres": to_int("regla_limite_lideres"),
        "capacidad_maxima": to_int("regla_capacidad_maxima"),
        "permite_subunidades": permite_subunidades,
        "requiere_aprobacion_lider": requiere_aprobacion,
        "unidad_privada": unidad_privada,
        # ═══════════════════════════════════════════════════════════════
        # PESTAÑAS VISIBLES
        # ═══════════════════════════════════════════════════════════════
        "pestana_liderazgo": pestana_liderazgo,
        "pestana_equipo_trabajo": pestana_equipo_trabajo,
        "pestana_actividades": pestana_actividades,
        "pestana_finanzas": pestana_finanzas,
        "pestana_reportes": pestana_reportes,
    }