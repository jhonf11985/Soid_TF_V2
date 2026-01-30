# agenda_app/models.py (al final) o en un archivo aparte importado
from django.db import models
from django.utils import timezone

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
