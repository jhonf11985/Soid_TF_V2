from datetime import date

from django.conf import settings
from django.db import models

from miembros_app.models import Miembro
from estructura_app.models import Unidad


class EvaluacionPerfilUnidad(models.Model):
    """
    Perfil de evaluación por UNIDAD (configura pesos y reglas).
    Perfil mixto:
    - Organizacional: asistencia, participación, compromiso, actitud, integración (1-5)
    - Espiritual: madurez espiritual (1-5) + estado espiritual (semántico)
    """
    # =========================
    # TIEMPO / PERIODICIDAD
    # =========================
    FREQ_MENSUAL = "MENSUAL"
    FREQ_TRIMESTRAL = "TRIMESTRAL"
    FREQ_SEMESTRAL = "SEMESTRAL"
    FREQ_ANUAL = "ANUAL"
    FREQ_LIBRE = "LIBRE"

    FRECUENCIAS = (
        (FREQ_MENSUAL, "Mensual"),
        (FREQ_TRIMESTRAL, "Trimestral"),
        (FREQ_SEMESTRAL, "Semestral"),
        (FREQ_ANUAL, "Anual"),
        (FREQ_LIBRE, "Libre"),
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    frecuencia = models.CharField(max_length=12, choices=FRECUENCIAS, default=FREQ_MENSUAL)
    dia_cierre = models.PositiveSmallIntegerField(default=28)

    auto_crear_periodo = models.BooleanField(default=True)
    permitir_editar_cerrada = models.BooleanField(default=False)

    # =========================
    # DIMENSIONES ACTIVAS
    # =========================
    usar_asistencia = models.BooleanField(default=True)
    usar_participacion = models.BooleanField(default=True)
    usar_compromiso = models.BooleanField(default=True)
    usar_actitud = models.BooleanField(default=True)
    usar_integracion = models.BooleanField(default=True)

    usar_madurez_espiritual = models.BooleanField(default=True)
    usar_estado_espiritual = models.BooleanField(default=True)


    MODO_MENSUAL = "MENSUAL"
    MODO_LIBRE = "LIBRE"

    MODOS = (
        (MODO_MENSUAL, "Mensual"),
        (MODO_LIBRE, "Libre"),
    )

    unidad = models.OneToOneField(
        "estructura_app.Unidad",
        on_delete=models.CASCADE,
        related_name="perfil_evaluacion",
    )

    modo = models.CharField(max_length=10, choices=MODOS, default=MODO_MENSUAL)

    # Pesos ORGANIZACIONAL
    w_asistencia = models.DecimalField(max_digits=4, decimal_places=2, default=0.18)
    w_participacion = models.DecimalField(max_digits=4, decimal_places=2, default=0.18)
    w_compromiso = models.DecimalField(max_digits=4, decimal_places=2, default=0.18)
    w_actitud = models.DecimalField(max_digits=4, decimal_places=2, default=0.13)
    w_integracion = models.DecimalField(max_digits=4, decimal_places=2, default=0.13)

    # Peso ESPIRITUAL (numérico)
    w_madurez_espiritual = models.DecimalField(max_digits=4, decimal_places=2, default=0.20)

    # El estado espiritual es semántico (no lleva peso; sirve como diagnóstico/bandera)
    excluir_evaluador = models.BooleanField(default=True)

    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Perfil evaluación - {self.unidad}"


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

    perfil = models.ForeignKey(
        "evaluaciones_app.EvaluacionPerfilUnidad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # ===== Diagnóstico general de la unidad (semántico, opcional)
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

    estado_workflow = models.CharField(
        max_length=20,
        choices=ESTADOS_WORKFLOW,
        default=ESTADO_BORRADOR,
    )

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
    Evaluación individual de un miembro dentro de una EvaluacionUnidad (período).
    Perfil mixto:
    - Organizacional: asistencia, participación, compromiso, actitud, integración (1-5)
    - Espiritual: madurez espiritual (1-5) + estado espiritual (semántico)
    """

    # 1-5
    PUNTAJES = (
        (1, "1"),
        (2, "2"),
        (3, "3"),
        (4, "4"),
        (5, "5"),
    )

    # Estado espiritual (semántico)
    ESTADO_ESTABLE = "ESTABLE"
    ESTADO_EN_CRECIMIENTO = "EN_CRECIMIENTO"
    ESTADO_EN_PROCESO = "EN_PROCESO"
    ESTADO_INESTABLE = "INESTABLE"
    ESTADO_EN_RIESGO = "EN_RIESGO"
    ESTADO_CRITICO = "CRITICO"
    ESTADO_AUSENTE = "AUSENTE"

    ESTADOS_ESPIRITUALES = (
        (ESTADO_ESTABLE, "🟢 Estable"),
        (ESTADO_EN_CRECIMIENTO, "🌱 En crecimiento"),
        (ESTADO_EN_PROCESO, "🧩 En proceso"),
        (ESTADO_INESTABLE, "🌊 Inestable"),
        (ESTADO_EN_RIESGO, "⚠️ En riesgo"),
        (ESTADO_CRITICO, "🔴 Crítico"),
        (ESTADO_AUSENTE, "⚫ Ausente"),
    )

    evaluacion = models.ForeignKey(
        EvaluacionUnidad,
        on_delete=models.CASCADE,
        related_name="items",
        null=True,
        blank=True,
    )

    miembro = models.ForeignKey(
        Miembro,
        on_delete=models.PROTECT,
        related_name="evaluaciones",
    )

    # ORGANIZACIONAL
    asistencia = models.PositiveSmallIntegerField(choices=PUNTAJES, default=3)
    participacion = models.PositiveSmallIntegerField(choices=PUNTAJES, default=3)
    compromiso = models.PositiveSmallIntegerField(choices=PUNTAJES, default=3)
    actitud = models.PositiveSmallIntegerField(choices=PUNTAJES, default=3)
    integracion = models.PositiveSmallIntegerField(choices=PUNTAJES, default=3)

    # ESPIRITUAL
    madurez_espiritual = models.PositiveSmallIntegerField(choices=PUNTAJES, default=3)
    estado_espiritual = models.CharField(
        max_length=20,
        choices=ESTADOS_ESPIRITUALES,
        default=ESTADO_ESTABLE,
    )

    # Resumen rápido (1-5)
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
            models.Index(fields=["estado_espiritual"]),
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
        - Promedio de 5 organizacionales + madurez espiritual
        - Penalización por estado espiritual (AUSENTE / EN_RIESGO / CRITICO)
        """
        base = round(
            (
                self.asistencia +
                self.participacion +
                self.compromiso +
                self.actitud +
                self.integracion +
                self.madurez_espiritual
            ) / 6
        )

        if self.estado_espiritual == self.ESTADO_AUSENTE:
            base = max(1, base - 2)
        elif self.estado_espiritual in (self.ESTADO_EN_RIESGO, self.ESTADO_CRITICO):
            base = max(1, base - 1)

        self.puntaje_general = int(min(5, max(1, base)))

    def save(self, *args, **kwargs):
        self.recalcular_puntaje_general()
        super().save(*args, **kwargs)
