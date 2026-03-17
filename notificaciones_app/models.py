# notificaciones_app/models.py

from django.conf import settings
from django.db import models

from tenants.models import Tenant


class Notification(models.Model):
    """
    Notificación sencilla para un usuario.
    Se puede usar para avisos internos del sistema.
    """

    TIPO_INFO = "info"
    TIPO_EXITO = "success"
    TIPO_ADVERTENCIA = "warning"
    TIPO_ERROR = "error"

    TIPO_CHOICES = [
        (TIPO_INFO, "Información"),
        (TIPO_EXITO, "Éxito"),
        (TIPO_ADVERTENCIA, "Advertencia"),
        (TIPO_ERROR, "Error"),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="Tenant",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="Usuario",
    )
    titulo = models.CharField(
        max_length=150,
        verbose_name="Título",
    )
    mensaje = models.TextField(
        blank=True,
        verbose_name="Mensaje",
    )
    url_destino = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="URL destino",
        help_text="Nombre de URL (reverse) o ruta absoluta para ir al hacer clic.",
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default=TIPO_INFO,
        verbose_name="Tipo",
    )
    leida = models.BooleanField(
        default=False,
        verbose_name="Leída",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=["tenant", "usuario", "leida"]),
        ]

    def __str__(self):
        return f"{self.titulo} → {self.usuario}"


class PushSubscription(models.Model):
    """
    Suscripción push para notificaciones web (VAPID).
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="Tenant",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )

    endpoint = models.TextField()
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)

    user_agent = models.CharField(max_length=255, blank=True, default="")
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Suscripción Push"
        verbose_name_plural = "Suscripciones Push"
        indexes = [
            models.Index(fields=["tenant", "user", "activo"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "endpoint"],
                name="unique_endpoint_per_tenant",
            ),
        ]

    def __str__(self):
        return f"PushSubscription({self.user_id}, tenant={self.tenant_id}, activo={self.activo})"