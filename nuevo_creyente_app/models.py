from django.conf import settings
from django.db import models
from django.utils import timezone

from miembros_app.models import Miembro


class NuevoCreyenteExpediente(models.Model):
    class Estados(models.TextChoices):
        EN_SEGUIMIENTO = "EN_SEGUIMIENTO", "En seguimiento"
        CERRADO = "CERRADO", "Cerrado"

    # 1 expediente por miembro (si luego quieres reabrir histórico, lo hacemos con un modelo de historiales)
    miembro = models.OneToOneField(
        Miembro,
        on_delete=models.CASCADE,
        related_name="expediente_nuevo_creyente",
        help_text="Miembro enviado al módulo de Nuevo Creyente."
    )
    unidad_responsable = models.ForeignKey(
        "estructura_app.Unidad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_nuevo_creyente",
        help_text="Unidad responsable del seguimiento del nuevo creyente."
    )


    estado = models.CharField(
        max_length=20,
        choices=Estados.choices,
        default=Estados.EN_SEGUIMIENTO,
        db_index=True
    )

    # Quién lo está llevando (puede ser null por ahora)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_nuevo_creyente"
    )
    # Padre espiritual (Miembro que acompaña)
    padres_espirituales = models.ManyToManyField(
        "miembros_app.Miembro",
        through="NuevoCreyentePadreEspiritual",
        blank=True,
        related_name="expedientes_nuevo_creyente_padrinos"
    )


    # Fechas clave
    fecha_envio = models.DateTimeField(default=timezone.now, db_index=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    proximo_contacto = models.DateField(null=True, blank=True)

    # Campos libres (los iremos refinando)
    notas = models.TextField(blank=True, default="")

    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Expediente (Nuevo Creyente)"
        verbose_name_plural = "Expedientes (Nuevo Creyente)"
        ordering = ["-fecha_envio", "-fecha_creacion"]

    def __str__(self):
        return f"NC - {self.miembro} ({self.get_estado_display()})"

class NuevoCreyentePadreEspiritual(models.Model):
    expediente = models.ForeignKey(
        "NuevoCreyenteExpediente",
        on_delete=models.CASCADE,
        related_name="padres_links"
    )
    padre = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.CASCADE,
        related_name="nuevo_creyente_padrino_links"
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("expediente", "padre")

    def __str__(self):
        return f"{self.expediente_id} -> {self.padre_id}"

