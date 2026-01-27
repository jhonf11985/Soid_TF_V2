from django.conf import settings
from django.db import models
from datetime import date

from miembros_app.models import Miembro
from estructura_app.models import Unidad


def current_year():
    return date.today().year


def current_month():
    return date.today().month


class EvaluacionUnidad(models.Model):
    """
    Evaluación por período para una unidad.
    Ej: Enero 2026 - Unidad Jóvenes.
    """

    # ===== Workflow de la evaluación (estado del proceso)
    ESTADO_BORRADOR = "BORRADOR"
    ESTADO_EN_PROGRESO = "EN_PROGRESO"
    ESTADO_CERRADA = "CERRADA"

    ESTADOS_WORKFLOW = (
        (ESTADO_BORRADOR, "Borrador"),
        (ESTADO_EN_PROGRESO, "En progreso"),
        (ESTADO_CERRADA, "Cerrada"),
    )

    # ===== Diagnóstico general (opcional, pero útil)
    DIAG_ESTABLE = "estable"
    DIAG_CRECIMIENTO = "crecimiento"
    DIAG_IRREGULAR = "irregular"
    DIAG_OBSERVACION = "observacion"
    DIAG_SEGUIMIENTO = "seguimiento"
    DIAG_RIESGO = "riesgo"
    DIAG_INACTIVO = "inactivo"

    DIAGNOSTICOS = (
        (DIAG_ESTABLE, "Estable"),
        (DIAG_CRECIMIENTO, "En crecimiento"),
        (DIAG_IRREGULAR, "Asistencia irregular"),
        (DIAG_OBSERVACION, "En observación"),
        (DIAG_SEGUIMIENTO, "En seguimiento"),
        (DIAG_RIESGO, "En riesgo"),
        (DIAG_INACTIVO, "Inactivo"),
    )

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name="evaluaciones_unidad",
    )

    anio = models.PositiveIntegerField(default=current_year)
    mes = models.PositiveSmallIntegerField(default=current_month)

    # Estado del proceso
    estado_workflow = models.CharField(
        max_length=20,
        choices=ESTADOS_WORKFLOW,
        default=ESTADO_BORRADOR,
    )

    # Diagnóstico general (esto NO es 1-5; es semántico)
    diagnostico = models.CharField(
        max_length=20,
        choices=DIAGNOSTICOS,
        default=DIAG_ESTABLE,
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluaciones_unidad_creadas",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    observaciones = models.TextField(blank=True, null=True)

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
            models.Index(fields=["estado_workflow"]),
            models.Index(fields=["diagnostico"]),
        ]

    def __str__(self):
        return f"Evaluación {self.mes:02d}/{self.anio} - {self.unidad}"


class EvaluacionMiembro(models.Model):
    """
    Evaluación de un miembro dentro de una unidad, ligada a un período (opcional)
    o simplemente a una fecha.
    """

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name="evaluaciones_miembros",
    )
    miembro = models.ForeignKey(
        Miembro,
        on_delete=models.CASCADE,
        related_name="evaluaciones",
    )

    # (Opcional, pero recomendado): vincular la evaluación del miembro al período
    evaluacion_unidad = models.ForeignKey(
        EvaluacionUnidad,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="detalle_miembros",
    )

    # =========================
    # DIMENSIONES SOID (1 a 5)
    # =========================
    asistencia = models.PositiveSmallIntegerField(default=3)
    participacion = models.PositiveSmallIntegerField(default=3)
    compromiso = models.PositiveSmallIntegerField(default=3)
    actitud = models.PositiveSmallIntegerField(default=3)
    integracion = models.PositiveSmallIntegerField(default=3)
    liderazgo = models.PositiveSmallIntegerField(default=3)

    # =========================
    # RESULTADOS CALCULADOS
    # =========================
    score_soid = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    clasificacion = models.CharField(max_length=50, blank=True, null=True)

    observaciones = models.TextField(blank=True, null=True)
    fecha = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Evaluación de miembro"
        verbose_name_plural = "Evaluaciones de miembros"
        ordering = ["-fecha"]
        constraints = [
            # Evita duplicar evaluaciones del mismo miembro el mismo día para la misma unidad
            models.UniqueConstraint(
                fields=["unidad", "miembro", "fecha"],
                name="uniq_eval_miembro_unidad_fecha",
            )
        ]
        indexes = [
            models.Index(fields=["unidad", "miembro", "fecha"]),
        ]

    def calcular_score(self):
        score = (
            self.asistencia * 0.20 +
            self.participacion * 0.20 +
            self.compromiso * 0.20 +
            self.actitud * 0.15 +
            self.integracion * 0.15 +
            self.liderazgo * 0.10
        )
        return round(score, 2)

    def calcular_clasificacion(self):
        score = float(self.score_soid)

        # Reglas inteligentes base
        if self.liderazgo >= 4 and self.compromiso >= 4 and self.asistencia >= 3:
            return "🟣 Líder potencial"

        if self.asistencia <= 2 and self.integracion <= 2:
            return "🔴 En riesgo"

        if self.asistencia >= 4 and self.participacion <= 2:
            return "🟠 Presente pero pasivo"

        if 2.5 <= score < 3.5:
            return "🟡 En desarrollo"

        if score >= 4.2:
            return "🟢 Comprometido"

        # fallback por score
        if score >= 4.5:
            return "🟢 Excelente"
        elif score >= 3.5:
            return "🔵 Bueno"
        elif score >= 2.5:
            return "🟡 Regular"
        elif score >= 1.5:
            return "🟠 Bajo"
        else:
            return "🔴 Crítico"

    def save(self, *args, **kwargs):
        self.score_soid = self.calcular_score()
        self.clasificacion = self.calcular_clasificacion()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.miembro} - {self.unidad} ({self.fecha})"


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
