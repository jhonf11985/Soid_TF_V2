# ia_app/services/safety.py
def safe_log_text(s: str, max_len: int = 500) -> str:
    """
    Evita logs gigantes.
    """
    s = (s or "").strip()
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s