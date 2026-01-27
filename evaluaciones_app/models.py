from django.conf import settings
from django.db import models
from django.utils import timezone



def current_year():
 return timezone.localdate().year

def current_month():
    return timezone.localdate().month

class EvaluacionUnidad(models.Model):
    """
    Una evaluación 'por período' para una unidad.
    Ej: Evaluación Enero 2026 - Unidad Jóvenes.
    """

    ESTADO_BORRADOR = "BORRADOR"
    ESTADO_EN_PROGRESO = "EN_PROGRESO"
    ESTADO_CERRADA = "CERRADA"

    ESTADOS = (
        (ESTADO_BORRADOR, "Borrador"),
        (ESTADO_EN_PROGRESO, "En progreso"),
        (ESTADO_CERRADA, "Cerrada"),
    )

    unidad = models.ForeignKey(
        "estructura_app.Unidad",
        on_delete=models.CASCADE,
        related_name="evaluaciones",
    )

    # Periodo simple para agrupar y hacer reportes

    anio = models.PositiveIntegerField(default=current_year)
    mes = models.PositiveSmallIntegerField(default=current_month)

    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_BORRADOR)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluaciones_unidad_creadas",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)



    class Meta:
        verbose_name = "Evaluación de unidad"
        verbose_name_plural = "Evaluaciones de unidad"
        ordering = ["-anio", "-mes", "unidad__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["unidad", "anio", "mes"],
                name="uniq_evaluacion_unidad_anio_mes",
            )
        ]
        indexes = [
            models.Index(fields=["unidad", "anio", "mes"]),
            models.Index(fields=["estado"]),
        ]

    def __str__(self):
        return f"Evaluación {self.mes:02d}/{self.anio} - {self.unidad}"


class EvaluacionMiembro(models.Model):
    """
    Evaluación individual de un miembro dentro de una EvaluacionUnidad.
    """

    # 1-5 (estrellas)
    PUNTAJES = (
        (1, "1"),
        (2, "2"),
        (3, "3"),
        (4, "4"),
        (5, "5"),
    )

    ESTADO_NORMAL = "NORMAL"
    ESTADO_EN_RIESGO = "EN_RIESGO"
    ESTADO_AUSENTE = "AUSENTE"

    ESTADOS = (
        (ESTADO_NORMAL, "Normal"),
        (ESTADO_EN_RIESGO, "En riesgo"),
        (ESTADO_AUSENTE, "Ausente"),
    )

    evaluacion = models.ForeignKey(
        EvaluacionUnidad,
        on_delete=models.CASCADE,
        related_name="items",
        null=True,
        blank=True,
    )

    miembro = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.PROTECT,
        related_name="evaluaciones",
    )

    asistencia = models.PositiveSmallIntegerField(choices=PUNTAJES, default=3)
    participacion = models.PositiveSmallIntegerField(choices=PUNTAJES, default=3)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_NORMAL)

    # Guardamos un resumen rápido (1-5) para ranking/estadísticas sin recalcular siempre.
    puntaje_general = models.PositiveSmallIntegerField(choices=PUNTAJES, default=3)

    observacion = models.CharField(max_length=255, blank=True, default="")

    evaluado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluaciones_miembro_creadas",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Evaluación de miembro"
        verbose_name_plural = "Evaluaciones de miembros"
        ordering = ["-creado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["evaluacion", "miembro"],
                name="uniq_evaluacion_miembro_por_periodo",
            )
        ]
        indexes = [
            models.Index(fields=["evaluacion"]),
            models.Index(fields=["miembro"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["puntaje_general"]),
        ]

    def __str__(self):
        return f"{self.miembro} ({self.evaluacion})"

    @property
    def estrellas(self):
        return "★" * int(self.puntaje_general or 0)

    def recalcular_puntaje_general(self):
        """
        Regla base (simple y útil):
        - Promedio de asistencia y participación
        - Penalización si está EN_RIESGO o AUSENTE
        """
        base = round((self.asistencia + self.participacion) / 2)

        if self.estado == self.ESTADO_AUSENTE:
            base = max(1, base - 2)
        elif self.estado == self.ESTADO_EN_RIESGO:
            base = max(1, base - 1)

        self.puntaje_general = int(min(5, max(1, base)))

    def save(self, *args, **kwargs):
        self.recalcular_puntaje_general()
        super().save(*args, **kwargs)
