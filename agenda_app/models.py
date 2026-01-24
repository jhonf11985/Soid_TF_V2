from django.db import models
from django.utils import timezone


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

    titulo = models.CharField(max_length=120)
    fecha = models.DateField()

    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.OTRO
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
