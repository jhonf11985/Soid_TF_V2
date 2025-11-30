from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def enviar_correo_sencillo(subject, body_html, destinatarios):
    """
    Envía un correo sencillo en HTML (con versión de texto plano).

    - subject: asunto del correo
    - body_html: contenido en HTML
    - destinatarios: string o lista de correos
    """
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]

    if not destinatarios:
        destinatarios = [settings.DEFAULT_FROM_EMAIL]

    # Versión de texto plano (por si el cliente de correo no soporta HTML)
    body_text = strip_tags(body_html)

    email = EmailMessage(
        subject=subject,
        body=body_html,
        from_email=settings.EMAIL_HOST_USER,
        to=destinatarios,
    )
    email.content_subtype = "html"  # el body es HTML
    email.extra_headers = {"X-Mailer": "Soid_Tf_2"}

    # Adjuntamos también la versión de texto plano como alternativa si quieres
    # (opcional; muchos clientes ya se apañan solo con HTML)
    # email.attach_alternative(body_text, "text/plain")

    email.send()
    return True


def enviar_correo_sistema(
    subject,
    heading=None,
    subheading=None,
    body_html=None,
    destinatarios=None,
    button_url=None,
    button_text=None,
    meta_text=None,
    extra_context=None,
    adjuntos=None,
):
    """
    Envía un correo usando la plantilla base del sistema:
    - subject: asunto
    - heading: título grande dentro del correo
    - subheading: subtítulo opcional
    - body_html: contenido HTML principal (se inyecta en el bloque central)
    - destinatarios: string o lista de correos
    - button_url / button_text: botón opcional
    - meta_text: texto pequeño al final (ej: 'Correo generado automáticamente')
    - extra_context: diccionario extra para la plantilla
    - adjuntos: lista de rutas de archivo a adjuntar (ruta absoluta en disco)
    """

    # Normalizar destinatarios
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]

    if not destinatarios:
        destinatarios = [settings.DEFAULT_FROM_EMAIL]

    contexto = {
        "subject": subject,
        "heading": heading or subject,
        "subheading": subheading,
        "body_html": body_html,
        "button_url": button_url,
        "button_text": button_text,
        "meta_text": meta_text,
    }

    if extra_context:
        contexto.update(extra_context)

    # Renderizamos la plantilla base del correo
    html = render_to_string("core/emails/base_email.html", contexto)
    body_text = strip_tags(html)

    email = EmailMessage(
        subject=subject,
        body=html,
        from_email=settings.EMAIL_HOST_USER,
        to=destinatarios,
    )
    email.content_subtype = "html"  # indicamos que el body es HTML
    email.extra_headers = {"X-Mailer": "Soid_Tf_2"}

    # Adjuntar archivos si se pasan
        # Adjuntar archivos si se pasan
    if adjuntos:
        for adj in adjuntos:
            if not adj:
                continue

            # Si es una ruta de archivo (str)
            if isinstance(adj, str):
                try:
                    email.attach_file(adj)
                except FileNotFoundError:
                    pass

            # Si es un archivo en memoria → (nombre, contenido_bytes)
            elif isinstance(adj, tuple) and len(adj) == 2:
                nombre, contenido = adj
                email.attach(nombre, contenido, "application/pdf")

    email.send()
    return True
