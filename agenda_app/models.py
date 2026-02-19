from django.db import models
from django.utils import timezone
from estructura_app.models import Unidad


class Actividad(models.Model):
    class Tipo(models.TextChoices):
        CULTO = "CULTO", "Culto"
        REUNION = "REUNION", "Reunión"
        EVENTO = "EVENTO", "Evento"
        ENSAYO = "ENSAYO", "Ensayo"
        CAMPANA = "CAMPANA", "Campaña"
        SOCIAL = "SOCIAL", "Actividad social"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        PROGRAMADA = "PROGRAMADA", "Programada"
        REALIZADA = "REALIZADA", "Realizada"
        CANCELADA = "CANCELADA", "Cancelada"
        
    class Visibilidad(models.TextChoices):
        PUBLICO = "PUBLICO", "Público"
        PRIVADO = "PRIVADO", "Privado"

    visibilidad = models.CharField(
        max_length=10,
        choices=Visibilidad.choices,
        default=Visibilidad.PRIVADO,   # por seguridad
        db_index=True
    )


    titulo = models.CharField(max_length=120)
    fecha = models.DateField()

    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.OTRO
    )


    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actividades_agenda",
        verbose_name="Unidad / Ministerio"
    )


    lugar = models.CharField(max_length=120, blank=True, default="")
    responsable_texto = models.CharField(max_length=120, blank=True, default="")
    descripcion = models.TextField(blank=True, default="")

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PROGRAMADA
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["fecha", "hora_inicio", "titulo"]
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"

    def __str__(self):
        return f"{self.fecha} - {self.titulo}"
from django.db import models

class ActividadRecordatorio(models.Model):
    actividad = models.ForeignKey(
        "agenda_app.Actividad",
        on_delete=models.CASCADE,
        related_name="recordatorios"
    )
    minutos_antes = models.PositiveIntegerField(default=60)
    enviado_en = models.DateTimeField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("actividad", "minutos_antes")]
        indexes = [
            models.Index(fields=["minutos_antes", "enviado_en"]),
        ]

    def __str__(self):
        return f"Recordatorio({self.actividad_id}, {self.minutos_antes}m)"
