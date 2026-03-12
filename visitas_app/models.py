from django.db import models

# Create your models here.
from django.db import models


class Visita(models.Model):
    TIPO_CHOICES = [
        ("visita", "Visita"),
        ("amigo", "Amigo"),
    ]

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("contactado", "Contactado"),
        ("seguimiento", "En seguimiento"),
        ("cerrado", "Cerrado"),
    ]

    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="visita")
    fecha_visita = models.DateField()
    primera_vez = models.BooleanField(default=True)
    invitado_por = models.CharField(max_length=150, blank=True, null=True)
    desea_contacto = models.BooleanField(default=True)
    peticion_oracion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente")
    notas = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_visita", "-id"]
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"

    def __str__(self):
        return f"{self.nombre} - {self.fecha_visita}"