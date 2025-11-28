from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.template.loader import render_to_string

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

def enviar_correo_sistema(
    subject,
    heading=None,
    subheading=None,
    body_html="",
    destinatarios=None,
    button_url=None,
    button_text=None,
    meta_text=None,
    extra_context=None,
):
    """
    Función genérica para enviar correos usando la plantilla base_email.html.
    Sirve para TODOS los módulos del sistema.
    """

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
        "meta_text": meta_text or "Este correo fue generado automáticamente por Soid_Tf_2.",
    }

    if extra_context:
        contexto.update(extra_context)

    html = render_to_string("core/emails/base_email.html", contexto)
    enviar_correo_sencillo(subject, html, destinatarios)