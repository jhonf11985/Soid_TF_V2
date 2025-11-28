from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags


def enviar_correo_sencillo(asunto, cuerpo_html, destinatarios):
    """
    Envía un correo HTML sencillo usando SIEMPRE el remitente del settings:

    - FROM: settings.EMAIL_HOST_USER (en tu caso: jhonf1_b@zoho.com)
    - TO: lista de destinatarios
    """

    # Aceptamos un string o una lista como destinatarios
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]

    from_email = getattr(settings, "EMAIL_HOST_USER", None)
    if not from_email:
        raise ValueError(
            "EMAIL_HOST_USER no está configurado en settings.py. "
            "Configura tu cuenta de Zoho en settings."
        )

    # Versión en texto plano
    text_body = strip_tags(cuerpo_html)

    msg = EmailMultiAlternatives(
        subject=asunto,
        body=text_body,
        from_email=from_email,  # <- remitente EXACTO = usuario Zoho
        to=destinatarios,
    )
    msg.attach_alternative(cuerpo_html, "text/html")
    msg.send()
