from django.db import models
from tenants.models import TenantAwareModel


class ClasificacionVisita(TenantAwareModel):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Clasificación de visita"
        verbose_name_plural = "Clasificaciones de visitas"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "nombre"],
                name="uniq_clasificacion_visita_nombre_por_tenant"
            )
        ]

    def __str__(self):
        return self.nombre


class Visita(TenantAwareModel):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("contactado", "Contactado"),
        ("seguimiento", "En seguimiento"),
        ("cerrado", "Cerrado"),
    ]

    GENERO_CHOICES = [
        ("M", "Masculino"),
        ("F", "Femenino"),
    ]

    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    genero = models.CharField(
        max_length=1,
        choices=GENERO_CHOICES,
    )
    edad = models.PositiveIntegerField(blank=True, null=True)

    clasificacion = models.ForeignKey(
        ClasificacionVisita,
        on_delete=models.PROTECT,
        related_name="visitas",
        blank=True,
        null=True,
    )

    primera_vez = models.BooleanField(default=True)
    fecha_primera_visita = models.DateField()
    fecha_ultima_visita = models.DateField()
    cantidad_visitas = models.PositiveIntegerField(default=1)

    invitado_por = models.CharField(max_length=150, blank=True, null=True)
    desea_contacto = models.BooleanField(default=True)
    peticion_oracion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente")
    notas = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_ultima_visita", "-id"]
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"

    def __str__(self):
        clasificacion = self.clasificacion.nombre if self.clasificacion else "Sin clasificación"
        return f"{self.nombre} - {clasificacion}"