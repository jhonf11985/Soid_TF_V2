from decimal import Decimal
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

    # Depreciación (activos)
    class MetodosDepreciacion(models.TextChoices):
        LINEA_RECTA = "LINEA_RECTA", "Línea recta"

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

    # Depreciación (calculada)
    deprecia = models.BooleanField(default=False)
    metodo_depreciacion = models.CharField(
        max_length=20,
        choices=MetodosDepreciacion.choices,
        default=MetodosDepreciacion.LINEA_RECTA
    )
    vida_util_anios = models.PositiveIntegerField(null=True, blank=True, help_text="Ej: 3, 5, 10")
    valor_residual_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Valor al final de la vida útil"
    )
    fecha_inicio_depreciacion = models.DateField(
        null=True, blank=True,
        help_text="Si está vacío, se usa fecha_compra"
    )

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

    # -----------------------------
    # Depreciación (propiedades)
    # -----------------------------
    @property
    def valor_total_costo(self):
        """
        Valor total a costo histórico (cantidad_total * costo_unitario).
        """
        if self.costo_unitario is None:
            return None
        return Decimal(self.cantidad_total) * self.costo_unitario

    def _fecha_inicio_dep(self):
        return self.fecha_inicio_depreciacion or self.fecha_compra

    def _anos_transcurridos(self):
        """
        Años transcurridos desde la fecha de inicio de depreciación.
        Se calcula por años completos (estable y simple).
        """
        f = self._fecha_inicio_dep()
        if not f:
            return 0

        hoy = timezone.now().date()
        anos = hoy.year - f.year
        if (hoy.month, hoy.day) < (f.month, f.day):
            anos -= 1
        return max(anos, 0)

    @property
    def depreciacion_anual_unitaria(self):
        """
        (costo_unitario - residual) / vida_util_anios
        """
        if not self.deprecia:
            return None
        if self.costo_unitario is None or not self.vida_util_anios:
            return None

        residual = self.valor_residual_unitario if self.valor_residual_unitario is not None else Decimal("0.00")
        base = self.costo_unitario - residual
        if base <= 0:
            return Decimal("0.00")

        return base / Decimal(self.vida_util_anios)

    @property
    def depreciacion_acumulada_unitaria(self):
        if not self.deprecia:
            return None

        anual = self.depreciacion_anual_unitaria
        if anual is None:
            return None

        anos = self._anos_transcurridos()

        residual = self.valor_residual_unitario if self.valor_residual_unitario is not None else Decimal("0.00")
        max_acum = (self.costo_unitario - residual) if self.costo_unitario is not None else Decimal("0.00")

        acum = anual * Decimal(anos)
        return min(acum, max_acum)

    @property
    def valor_en_libros_unitario(self):
        """
        costo_unitario - depreciacion_acumulada_unitaria (con tope residual)
        """
        if self.costo_unitario is None:
            return None

        if not self.deprecia:
            return self.costo_unitario

        acum = self.depreciacion_acumulada_unitaria
        if acum is None:
            return None

        residual = self.valor_residual_unitario if self.valor_residual_unitario is not None else Decimal("0.00")
        valor = self.costo_unitario - acum
        return max(valor, residual)

    @property
    def valor_en_libros_total(self):
        """
        cantidad_total * valor_en_libros_unitario
        """
        v = self.valor_en_libros_unitario
        if v is None:
            return None
        return Decimal(self.cantidad_total) * v

    @property
    def depreciacion_acumulada_total(self):
        """
        cantidad_total * depreciacion_acumulada_unitaria
        """
        d = self.depreciacion_acumulada_unitaria
        if d is None:
            return None
        return Decimal(self.cantidad_total) * d


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
    ubicacion_origen = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, related_name="movimientos_origen",
        blank=True, null=True
    )
    ubicacion_destino = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, related_name="movimientos_destino",
        blank=True, null=True
    )

    motivo = models.CharField(max_length=255, blank=True)
    notas = models.TextField(blank=True)

    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Movimiento de recurso"
        verbose_name_plural = "Movimientos de recursos"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.get_tipo_display()} | {self.recurso.codigo} | {self.cantidad}"
