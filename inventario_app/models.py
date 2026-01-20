from django.db import models
from django.utils import timezone


class CategoriaRecurso(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría de recurso"
        verbose_name_plural = "Categorías de recursos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Ubicacion(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Recurso(models.Model):
    class Estados(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        EN_USO = "EN_USO", "En uso"
        PRESTADO = "PRESTADO", "Prestado"
        EN_REPARACION = "EN_REPARACION", "En reparación"
        DANADO = "DANADO", "Dañado"
        BAJA = "BAJA", "Baja"

    class Condiciones(models.TextChoices):
        NUEVO = "NUEVO", "Nuevo"
        BUENO = "BUENO", "Bueno"
        REGULAR = "REGULAR", "Regular"
        MALO = "MALO", "Malo"

    # Básico
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(CategoriaRecurso, on_delete=models.PROTECT, related_name="recursos")
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name="recursos")
    cantidad_total = models.PositiveIntegerField(default=1)
    estado = models.CharField(max_length=20, choices=Estados.choices, default=Estados.DISPONIBLE)

    # Prioridad 1: Ficha técnica
    marca = models.CharField(max_length=120, blank=True)
    modelo = models.CharField(max_length=120, blank=True)
    numero_serie = models.CharField(max_length=120, blank=True)

    # Prioridad 2: Operación / condición
    condicion_fisica = models.CharField(
        max_length=20,
        choices=Condiciones.choices,
        default=Condiciones.BUENO
    )
    es_consumible = models.BooleanField(default=False)
    requiere_mantenimiento = models.BooleanField(default=False)

    # Prioridad 3: Compra / garantía
    fecha_compra = models.DateField(null=True, blank=True)
    proveedor = models.CharField(max_length=150, blank=True)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    garantia_hasta = models.DateField(null=True, blank=True)

    # Otros
    descripcion = models.TextField(blank=True)
    foto = models.ImageField(upload_to="inventario/recursos/", blank=True, null=True)

    creado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Recurso"
        verbose_name_plural = "Recursos"
        ordering = ["nombre", "codigo"]
        indexes = [
            models.Index(fields=["codigo"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["numero_serie"]),
            models.Index(fields=["condicion_fisica"]),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class MovimientoRecurso(models.Model):
    class Tipos(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"
        TRASLADO = "TRASLADO", "Traslado"
        REPARACION = "REPARACION", "Enviado a reparación"
        BAJA = "BAJA", "Baja"

    recurso = models.ForeignKey(Recurso, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=Tipos.choices)
    cantidad = models.PositiveIntegerField(default=1)
    ubicacion_origen = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name="movimientos_origen", blank=True, null=True)
    ubicacion_destino = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name="movimientos_destino", blank=True, null=True)

    motivo = models.CharField(max_length=255, blank=True)
    notas = models.TextField(blank=True)

    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Movimiento de recurso"
        verbose_name_plural = "Movimientos de recursos"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.get_tipo_display()} | {self.recurso.codigo} | {self.cantidad}"
