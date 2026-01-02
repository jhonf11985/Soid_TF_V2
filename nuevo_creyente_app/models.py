from django.conf import settings
from django.db import models
from django.utils import timezone

from miembros_app.models import Miembro


class NuevoCreyenteExpediente(models.Model):
    class Estados(models.TextChoices):
        EN_SEGUIMIENTO = "EN_SEGUIMIENTO", "En seguimiento"
        CERRADO = "CERRADO", "Cerrado"

    class Etapas(models.TextChoices):
        INICIO = "INICIO", "Inicio"
        PRIMER_CONTACTO = "PRIMER_CONTACTO", "Primer contacto"
        ACOMPANAMIENTO = "ACOMPANAMIENTO", "Acompañamiento"
        INTEGRACION = "INTEGRACION", "Integración"
        EVALUACION = "EVALUACION", "Evaluación"
        CIERRE = "CIERRE", "Cierre"

    ETAPAS_ORDEN = [
        Etapas.INICIO,
        Etapas.PRIMER_CONTACTO,
        Etapas.ACOMPANAMIENTO,
        Etapas.INTEGRACION,
        Etapas.EVALUACION,
        Etapas.CIERRE,
    ]

    miembro = models.OneToOneField(
        Miembro,
        on_delete=models.CASCADE,
        related_name="expediente_nuevo_creyente",
        help_text="Miembro enviado al módulo de Nuevo Creyente.",
    )

    unidad_responsable = models.ForeignKey(
        "estructura_app.Unidad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_nuevo_creyente",
        help_text="Unidad responsable del seguimiento del nuevo creyente.",
    )

    estado = models.CharField(
        max_length=20,
        choices=Estados.choices,
        default=Estados.EN_SEGUIMIENTO,
        db_index=True,
    )

    etapa = models.CharField(
        max_length=30,
        choices=Etapas.choices,
        default=Etapas.INICIO,
        db_index=True,
        help_text="Etapa actual del ciclo de seguimiento (manual asistido).",
    )

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_nuevo_creyente",
    )

    padres_espirituales = models.ManyToManyField(
        "miembros_app.Miembro",
        through="NuevoCreyentePadreEspiritual",
        blank=True,
        related_name="expedientes_nuevo_creyente_padrinos",
    )

    fecha_envio = models.DateTimeField(default=timezone.now, db_index=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    proximo_contacto = models.DateField(null=True, blank=True)

    notas = models.TextField(blank=True, default="")

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Expediente (Nuevo Creyente)"
        verbose_name_plural = "Expedientes (Nuevo Creyente)"
        ordering = ["-fecha_envio", "-fecha_creacion"]

    def __str__(self):
        return f"NC - {self.miembro} ({self.get_estado_display()})"

    def etapa_index(self):
        try:
            return self.ETAPAS_ORDEN.index(self.etapa)
        except ValueError:
            return 0

    def etapa_sugerencia(self):
        return {
            self.Etapas.INICIO: "Asigna responsable y define el próximo contacto.",
            self.Etapas.PRIMER_CONTACTO: "Recomendado: llamada o mensaje en 3–5 días.",
            self.Etapas.ACOMPANAMIENTO: "Acompaña con un segundo contacto y escucha activa.",
            self.Etapas.INTEGRACION: "Invita a célula / grupo pequeño o actividad sencilla.",
            self.Etapas.EVALUACION: "Evalúa barreras y define el siguiente paso (discipulado, célula, etc.).",
            self.Etapas.CIERRE: "Seguimiento completado. Ya no requiere cuidado intensivo.",
        }.get(self.etapa, "")

    def puede_cerrar(self):
        return self.estado == self.Estados.EN_SEGUIMIENTO and self.etapa == self.Etapas.EVALUACION

    def cerrar(self, user=None):
        self.estado = self.Estados.CERRADO
        self.etapa = self.Etapas.CIERRE
        self.fecha_cierre = timezone.now()
        self.save(update_fields=["estado", "etapa", "fecha_cierre", "fecha_actualizacion"])


class NuevoCreyentePadreEspiritual(models.Model):
    expediente = models.ForeignKey(
        "NuevoCreyenteExpediente",
        on_delete=models.CASCADE,
        related_name="padres_links",
    )
    padre = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.CASCADE,
        related_name="nuevo_creyente_padrino_links",
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("expediente", "padre")

    def __str__(self):
        return f"{self.expediente_id} -> {self.padre_id}"
