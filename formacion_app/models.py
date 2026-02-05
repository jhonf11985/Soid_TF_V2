from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class ProgramaEducativo(models.Model):
    """
    Plantilla/definición del programa. Ej: 'Escuela Dominical', 'Discipulado Básico'
    """
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    TIPO_CHOICES = (
        ("CONTINUO", "Continuo"),
        ("POR_CICLO", "Por ciclo"),
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="POR_CICLO")

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Programa educativo"
        verbose_name_plural = "Programas educativos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class CicloPrograma(models.Model):
    """
    Ejecución/periodo de un programa. Ej: 'Escuela Dominical 2026'
    """
    programa = models.ForeignKey(ProgramaEducativo, on_delete=models.PROTECT, related_name="ciclos")
    nombre = models.CharField(max_length=120)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ciclo de programa"
        verbose_name_plural = "Ciclos de programa"
        unique_together = (("programa", "nombre"),)
        ordering = ["-id"]

    def __str__(self):
        return f"{self.programa} - {self.nombre}"


class GrupoFormativo(models.Model):
    """
    Grupo / clase formativa.
    Puede existir de forma independiente o estar asignado a un programa.
    """

    SEXO_CHOICES = (
        ("VARONES", "Varones"),
        ("HEMBRAS", "Hembras"),
        ("MIXTO", "Mixto"),
    )

    # =========================================================================
    # NUEVA REGLA: ESTADO CIVIL PERMITIDO
    # =========================================================================
    ESTADO_CIVIL_CHOICES = (
        ("TODOS", "Todos"),
        ("SOLTERO", "Solteros"),
        ("CASADO", "Casados"),
        ("VIUDO", "Viudos"),
        ("DIVORCIADO", "Divorciados"),
    )

    programa = models.ForeignKey(
        ProgramaEducativo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grupos",
        help_text="Programa educativo al que pertenece (opcional).",
    )

    ciclo = models.ForeignKey(
        "CicloPrograma",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grupos",
        help_text="Ciclo del programa (opcional).",
    )

    nombre = models.CharField(max_length=120)

    sexo_permitido = models.CharField(
        max_length=10,
        choices=SEXO_CHOICES,
        default="MIXTO",
    )

    estado_civil_permitido = models.CharField(
        max_length=15,
        choices=ESTADO_CIVIL_CHOICES,
        default="TODOS",
        help_text="Filtro por estado civil para sugerencias de alumnos.",
    )

    edad_min = models.PositiveSmallIntegerField(null=True, blank=True)
    edad_max = models.PositiveSmallIntegerField(null=True, blank=True)

    # =========================================================================
    # EQUIPO DEL GRUPO (ManyToMany a Miembro)
    # =========================================================================
    maestros = models.ManyToManyField(
        'miembros_app.Miembro',
        blank=True,
        related_name="grupos_como_maestro",
        help_text="Maestros responsables del grupo.",
    )

    ayudantes = models.ManyToManyField(
        'miembros_app.Miembro',
        blank=True,
        related_name="grupos_como_ayudante",
        help_text="Ayudantes del grupo.",
    )

    # Campo legacy - mantener por compatibilidad o eliminar después de migrar
    maestro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grupos_formativos_legacy",
        help_text="(Legacy) Usuario responsable del grupo.",
    )

    horario = models.CharField(max_length=120, blank=True)
    lugar = models.CharField(max_length=120, blank=True)
    cupo = models.PositiveSmallIntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Grupo formativo"
        verbose_name_plural = "Grupos formativos"
        ordering = ["nombre"]
        unique_together = (("programa", "nombre"),)

    def __str__(self):
        if self.programa:
            return f"{self.programa} | {self.nombre}"
        return self.nombre

    def clean(self):
        if self.edad_min is not None and self.edad_max is not None:
            if self.edad_min > self.edad_max:
                raise ValidationError("edad_min no puede ser mayor que edad_max.")

    # =========================================================================
    # MÉTODOS ÚTILES
    # =========================================================================
    def get_estudiantes_activos(self):
        """Retorna los miembros inscritos con estado ACTIVO."""
        return self.inscripciones.filter(estado="ACTIVO").select_related('miembro')

    def total_estudiantes_activos(self):
        """Cuenta estudiantes activos."""
        return self.inscripciones.filter(estado="ACTIVO").count()

    def tiene_cupo_disponible(self):
        """Verifica si hay cupo disponible."""
        if self.cupo is None:
            return True
        return self.total_estudiantes_activos() < self.cupo


class InscripcionGrupo(models.Model):
    """
    Inscripción de un miembro a un grupo formativo.
    """
    ESTADO_CHOICES = (
        ("ACTIVO", "Activo"),
        ("RETIRADO", "Retirado"),
        ("FINALIZADO", "Finalizado"),
    )

    miembro = models.ForeignKey(
        'miembros_app.Miembro',
        on_delete=models.CASCADE,
        related_name="inscripciones_formacion",
        help_text="Miembro inscrito en el grupo.",
    )

    grupo = models.ForeignKey(
        GrupoFormativo,
        on_delete=models.CASCADE,
        related_name="inscripciones",
    )

    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default="ACTIVO")
    fecha_inscripcion = models.DateField(default=timezone.now)
    nota = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["miembro", "grupo"],
                name="uniq_miembro_grupo",
            )
        ]

    def __str__(self):
        return f"{self.miembro} -> {self.grupo}"

    def clean(self):
        """
        Regla: si el grupo está asignado a un programa,
        el miembro no puede estar en 2 grupos del mismo programa.
        """
        programa = self.grupo.programa
        if not programa:
            return

        qs = InscripcionGrupo.objects.filter(
            miembro=self.miembro,
            grupo__programa=programa,
            estado="ACTIVO",
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.exists():
            raise ValidationError("Este miembro ya está inscrito en otro grupo de este programa.")