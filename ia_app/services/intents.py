# ia_app/services/intents.py
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from .text_utils import normalize_text, extract_first_int


@dataclass
class ParsedQuery:
    intent: str
    params: Dict[str, Any]
    confidence: float
    normalized: str


# Palabras "ruido" que podemos ignorar (no es obligatorio, pero ayuda)
STOPWORDS = {
    "por", "favor", "porfa", "me", "porfavor", "oye", "mira", "quiero", "necesito",
    "dime", "dame", "busca", "buscame", "buscame", "muestreme", "muestrame",
    "enseneme", "enseñame", "ensename", "traeme", "traeme", "ponme"
}

# Sinónimos por grupos (puedes expandirlos luego)
GROUP_RECENT = {
    "ultimos", "ultimo", "recientes", "reciente", "nuevos", "nuevo", "mas nuevos",
    "mas reciente", "mas recientes", "recien", "recien registrados"
}

GROUP_MEMBER = {
    "miembros", "miembro", "hermanos", "hermano", "personas", "persona"
}

GROUP_REGISTER = {
    "registrados", "registrado", "registro", "ingresados", "ingresado",
    "inscritos", "inscrito", "ingreso", "entraron", "entrado"
}

GROUP_TIME_TODAY = {"hoy", "en el dia", "en el dia de hoy"}
GROUP_TIME_YESTERDAY = {"ayer"}
GROUP_TIME_WEEK = {"esta semana", "en la semana", "semanal"}
GROUP_TIME_MONTH = {"este mes", "en el mes", "mensual"}

# Intent names
INTENT_ULTIMOS_MIEMBROS = "ultimos_miembros"
INTENT_MIEMBROS_HOY = "miembros_hoy"
INTENT_MIEMBROS_SEMANA = "miembros_semana"
INTENT_MIEMBROS_MES = "miembros_mes"
INTENT_BUSCAR_NOMBRE = "buscar_nombre"
INTENT_UNKNOWN = "unknown"


def _contains_any(text: str, options: set[str]) -> bool:
    for opt in options:
        if opt in text:
            return True
    return False


def _score_recent_members(text: str) -> float:
    """
    Puntuación simple para detectar "últimos miembros registrados" aunque sea fluido.
    """
    score = 0.0
    if _contains_any(text, GROUP_RECENT):
        score += 0.45
    if _contains_any(text, GROUP_MEMBER):
        score += 0.30
    if _contains_any(text, GROUP_REGISTER):
        score += 0.25
    return min(score, 1.0)


def parse_intent(raw_text: str) -> ParsedQuery:
    """
    Convierte texto libre -> intent + params.
    Versión 1: reglas + sinónimos (ligero).
    """
    text = normalize_text(raw_text)

    # Parámetros comunes
    limit = extract_first_int(text, default=10, max_limit=50)

    # 1) Consultas por tiempo directo (hoy/semana/mes) si menciona miembros + registro
    is_member = _contains_any(text, GROUP_MEMBER)
    is_register = _contains_any(text, GROUP_REGISTER)

    if is_member and is_register:
        if _contains_any(text, GROUP_TIME_TODAY):
            return ParsedQuery(INTENT_MIEMBROS_HOY, {"limit": limit, "range": "today"}, 0.95, text)
        if _contains_any(text, GROUP_TIME_YESTERDAY):
            # lo tratamos como hoy pero con range=yesterday (lo implementamos luego en queries)
            return ParsedQuery(INTENT_MIEMBROS_HOY, {"limit": limit, "range": "yesterday"}, 0.90, text)
        if _contains_any(text, GROUP_TIME_WEEK):
            return ParsedQuery(INTENT_MIEMBROS_SEMANA, {"limit": limit, "range": "week"}, 0.92, text)
        if _contains_any(text, GROUP_TIME_MONTH):
            return ParsedQuery(INTENT_MIEMBROS_MES, {"limit": limit, "range": "month"}, 0.92, text)

    # 2) "últimos / recientes" + miembros + (registrados opcional)
    score = _score_recent_members(text)
    if score >= 0.60:
        return ParsedQuery(INTENT_ULTIMOS_MIEMBROS, {"limit": limit}, score, text)

    # 3) Buscar por nombre (muy básico)
    # Ej: "busca juan perez", "encuentra maria"
    # Regla: si aparece "busca" o "encuentra" y luego hay texto no vacío
    if ("busca " in text) or ("encuentra " in text) or ("buscar " in text):
        # intenta extraer lo que viene después del primer verbo
        target = text
        for prefix in ("busca ", "encuentra ", "buscar "):
            if prefix in text:
                target = text.split(prefix, 1)[1].strip()
                break
        if target:
            return ParsedQuery(INTENT_BUSCAR_NOMBRE, {"q": target, "limit": limit}, 0.85, text)

    return ParsedQuery(INTENT_UNKNOWN, {"limit": limit}, 0.10, text)