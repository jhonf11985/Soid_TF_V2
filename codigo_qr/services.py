import secrets


def generar_token(longitud_bytes: int = 24) -> str:
    """
    Genera un token seguro para QR.
    24 bytes => token_urlsafe corto y robusto para usar en URLs/QR.
    """
    return secrets.token_urlsafe(longitud_bytes)
