import os
import shutil
from django.conf import settings


def get_chrome_executable():
    """
    Devuelve la ruta válida a Chrome/Chromium:
    1) Si CHROME_PATH existe y es real → lo usa.
    2) Si no, intenta encontrar Chrome/Chromium automáticamente.
    3) Si nada funciona, devuelve None.
    """

    # 1) Ruta desde variable de entorno / settings
    chrome_path = settings.CHROME_PATH
    if chrome_path and os.path.exists(chrome_path):
        return chrome_path

    # 2) Buscar ejecutables típicos en Windows y Linux
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]

    for c in candidates:
        if c:
            return c

    # 3) No encontrado
    return None
