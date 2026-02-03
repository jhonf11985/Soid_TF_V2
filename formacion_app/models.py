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

    # Opcional (para futuro): tipo de programa
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
    nombre = models.CharField(max_length=120)  # Ej: '2026', 'Trimestre 1 - 2026'
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
    Grupo/clase dentro de un ciclo. Ej: 'Varones 18-30'
    """
    SEXO_CHOICES = (
        ("VARONES", "Varones"),
        ("HEMBRAS", "Hembras"),
        ("MIXTO", "Mixto"),
    )

    ciclo = models.ForeignKey(CicloPrograma, on_delete=models.CASCADE, related_name="grupos")
    nombre = models.CharField(max_length=120)

    sexo_permitido = models.CharField(max_length=10, choices=SEXO_CHOICES, default="MIXTO")
    edad_min = models.PositiveSmallIntegerField(null=True, blank=True)
    edad_max = models.PositiveSmallIntegerField(null=True, blank=True)

    maestro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grupos_formacion",
        help_text="Usuario maestro/facilitador responsable (por ahora User).",
    )

    horario = models.CharField(max_length=120, blank=True)   # Ej: 'Domingos 9:00 AM'
    lugar = models.CharField(max_length=120, blank=True)     # Ej: 'Aula 2'
    cupo = models.PositiveSmallIntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Grupo formativo"
        verbose_name_plural = "Grupos formativos"
        unique_together = (("ciclo", "nombre"),)
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.ciclo} | {self.nombre}"

    def clean(self):
        # Validación básica de rangos de edad
        if self.edad_min is not None and self.edad_max is not None:
            if self.edad_min > self.edad_max:
                raise ValidationError("edad_min no puede ser mayor que edad_max.")


class InscripcionGrupo(models.Model):
    """
    Un miembro puede estar en varios programas, PERO:
    - En un mismo ciclo, el miembro solo puede estar en 1 grupo (regla #2 del negocio)
    """
    ESTADO_CHOICES = (
        ("ACTIVO", "Activo"),
        ("RETIRADO", "Retirado"),
        ("FINALIZADO", "Finalizado"),
    )

    # Ajusta esta importación a tu modelo real de Miembro
    # Si tu app se llama miembros_app y el modelo es Miembro:
    # from miembros_app.models import Miembro
    # miembro = models.ForeignKey(Miembro, ...)

    miembro_id = models.PositiveIntegerField(help_text="ID del Miembro (temporal).")  # Placeholder para integrar luego
    grupo = models.ForeignKey(GrupoFormativo, on_delete=models.CASCADE, related_name="inscripciones")
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default="ACTIVO")
    fecha_inscripcion = models.DateField(default=timezone.now)
    nota = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"
        ordering = ["-id"]

        # Regla: un miembro NO puede estar en 2 grupos del mismo ciclo.
        # Como aún no enlazamos a Miembro real, aplicamos la regla con miembro_id + ciclo
        constraints = [
            models.UniqueConstraint(
                fields=["miembro_id", "grupo"],
                name="uniq_miembro_grupo",
            )
        ]

    def __str__(self):
        return f"Miembro {self.miembro_id} -> {self.grupo}"

    def clean(self):
        # Bloquear que el mismo miembro esté en 2 grupos del mismo ciclo
        ciclo = self.grupo.ciclo
        qs = InscripcionGrupo.objects.filter(miembro_id=self.miembro_id, grupo__ciclo=ciclo)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("Este miembro ya está inscrito en otro grupo de este ciclo.")
