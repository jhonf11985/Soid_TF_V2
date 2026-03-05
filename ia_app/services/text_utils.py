# ia_app/services/text_utils.py
import re
import unicodedata


def strip_accents(s: str) -> str:
    """
    Quita tildes/acentos: "últimos" -> "ultimos"
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def normalize_text(s: str) -> str:
    """
    Normaliza texto para comparar:
    - minúsculas
    - sin tildes
    - espacios limpios
    """
    s = (s or "").strip().lower()
    s = strip_accents(s)
    s = re.sub(r"\s+", " ", s)
    return s


def extract_first_int(s: str, default: int = 10, max_limit: int = 50) -> int:
    """
    Extrae el primer número que aparezca en el texto (1..999).
    """
    if not s:
        return default
    m = re.search(r"\b(\d{1,3})\b", s)
    if not m:
        return default
    n = int(m.group(1))
    if n < 1:
        return default
    return min(n, max_limit)