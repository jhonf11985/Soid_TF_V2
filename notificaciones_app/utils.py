# notificaciones_app/utils.py

from django.urls import reverse, NoReverseMatch
from .models import Notification


def crear_notificacion(
    usuario,
    titulo,
    mensaje="",
    url_name=None,
    tipo="info",
):
    """
    Crea una notificación para un usuario.

    - usuario: instancia de User (request.user, por ejemplo)
    - titulo: texto corto que se mostrará en la lista
    - mensaje: texto más largo (opcional)
    - url_name: nombre de URL de Django, por ejemplo "miembros_app:dashboard"
                Si no se puede resolver, se guarda tal cual (por si es una ruta absoluta).
    - tipo: "info", "success", "warning", "error"
    """

    url_destino = ""

    if url_name:
        try:
            # Intentamos resolver el nombre de URL a una ruta real
            url_destino = reverse(url_name)
        except NoReverseMatch:
            # Si falla, guardamos el valor tal cual (por si es un path directo)
            url_destino = url_name

    return Notification.objects.create(
        usuario=usuario,
        titulo=titulo,
        mensaje=mensaje,
        url_destino=url_destino,
        tipo=tipo,
    )
