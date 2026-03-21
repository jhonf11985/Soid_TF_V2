from django.db import models
from django.utils import timezone
from tenants.models import TenantAwareModel


class TipoRegistroVisita(TenantAwareModel):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Tipo de registro de visita"
        verbose_name_plural = "Tipos de registros de visitas"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "nombre"],
                name="uniq_tipo_registro_visita_nombre_por_tenant"
            )
        ]

    def __str__(self):
        return self.nombre


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


class RegistroVisitas(TenantAwareModel):
    ESTADO_CHOICES = [
        ("abierto", "Abierto"),
        ("cerrado", "Cerrado"),
    ]

    fecha = models.DateField(default=timezone.localdate)

    tipo = models.ForeignKey(
        TipoRegistroVisita,
        on_delete=models.PROTECT,
        related_name="registros",
    )

    unidad_responsable = models.ForeignKey(
        "estructura_app.Unidad",
        on_delete=models.PROTECT,
        related_name="registros_visitas",
        null=True,
        blank=True,
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="abierto",
    )

    observaciones = models.TextField(blank=True, null=True)

    # ═══════════════════════════════════════════════════════════════
    # Auditoría de cierre
    # ═══════════════════════════════════════════════════════════════
    cerrado_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de cierre",
    )
    cerrado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_visitas_cerrados",
        verbose_name="Cerrado por",
    )

    # ═══════════════════════════════════════════════════════════════
    # Auditoría de reapertura (opcional, para historial)
    # ═══════════════════════════════════════════════════════════════
    reabierto_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de reapertura",
    )
    reabierto_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_visitas_reabiertos",
        verbose_name="Reabierto por",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Registro de visitas"
        verbose_name_plural = "Registros de visitas"
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["tipo"]),
            models.Index(fields=["estado"]),
        ]

    def __str__(self):
        tipo = self.tipo.nombre if self.tipo_id else "Sin tipo"
        unidad = self.unidad_responsable.nombre if self.unidad_responsable_id else "Sin unidad"
        return f"{self.fecha} - {tipo} - {unidad}"

    @property
    def esta_cerrado(self):
        return self.estado == "cerrado"

    @property
    def esta_abierto(self):
        return self.estado == "abierto"

    def cerrar(self, usuario):
        """Cierra el registro con auditoría."""
        self.estado = "cerrado"
        self.cerrado_at = timezone.now()
        self.cerrado_por = usuario
        self.save(update_fields=["estado", "cerrado_at", "cerrado_por", "updated_at"])

    def reabrir(self, usuario):
        """Reabre el registro con auditoría."""
        self.estado = "abierto"
        self.reabierto_at = timezone.now()
        self.reabierto_por = usuario
        # Limpiar datos de cierre anterior
        self.cerrado_at = None
        self.cerrado_por = None
        self.save(update_fields=[
            "estado", "reabierto_at", "reabierto_por",
            "cerrado_at", "cerrado_por", "updated_at"
        ])


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

    registro = models.ForeignKey(
        RegistroVisitas,
        on_delete=models.CASCADE,
        related_name="visitas",
        null=True,
        blank=True,
    )

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
    fecha_primera_visita = models.DateField(blank=True, null=True)
    fecha_ultima_visita = models.DateField(blank=True, null=True)
    cantidad_visitas = models.PositiveIntegerField(default=1)

    invitado_por = models.CharField(max_length=150, blank=True, null=True)
    desea_contacto = models.BooleanField(default=True)
    peticion_oracion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente")
    notas = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"
        indexes = [
            models.Index(fields=["registro"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["telefono"]),
        ]

    def save(self, *args, **kwargs):
        if self.registro_id and not getattr(self, "tenant_id", None):
            self.tenant = self.registro.tenant

        if not self.fecha_primera_visita:
            self.fecha_primera_visita = self.registro.fecha if self.registro_id else timezone.localdate()

        self.fecha_ultima_visita = self.registro.fecha if self.registro_id else timezone.localdate()

        super().save(*args, **kwargs)

    def __str__(self):
        clasificacion = self.clasificacion.nombre if self.clasificacion else "Sin clasificación"
        return f"{self.nombre} - {clasificacion}"