from django.db import models
from django.conf import settings


class CuentaFinanciera(models.Model):
    TIPO_CUENTA_CHOICES = [
        ("caja", "Caja"),
        ("banco", "Banco"),
        ("otro", "Otro"),
    ]

    nombre = models.CharField(
        max_length=100,
        help_text="Nombre de la cuenta. Ej: Caja general, Banco Popular, etc."
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CUENTA_CHOICES,
        default="caja",
        help_text="Tipo de cuenta (caja, banco u otro)."
    )
    moneda = models.CharField(
        max_length=10,
        default="DOP",
        help_text="Moneda principal de la cuenta. Ej: DOP, USD."
    )
    saldo_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Saldo inicial de la cuenta al empezar a usar el sistema."
    )
    esta_activa = models.BooleanField(
        default=True,
        help_text="Permite activar o desactivar la cuenta sin borrarla."
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cuenta financiera"
        verbose_name_plural = "Cuentas financieras"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.moneda})"


class CategoriaMovimiento(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [
        ("ingreso", "Ingreso"),
        ("egreso", "Egreso"),
    ]

    nombre = models.CharField(
        max_length=100,
        help_text="Nombre de la categoría. Ej: Diezmo, Ofrenda, Electricidad."
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_MOVIMIENTO_CHOICES,
        help_text="Indica si la categoría es de ingreso o de egreso."
    )
    es_editable = models.BooleanField(
        default=True,
        help_text="Si se desactiva, la categoría no se podrá borrar fácilmente."
    )

    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categoría de movimiento"
        verbose_name_plural = "Categorías de movimientos"
        ordering = ["tipo", "nombre"]

    def __str__(self):
        tipo_str = "Ingreso" if self.tipo == "ingreso" else "Egreso"
        return f"{self.nombre} ({tipo_str})"


class MovimientoFinanciero(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [
        ("ingreso", "Ingreso"),
        ("egreso", "Egreso"),
    ]

    fecha = models.DateField(
        help_text="Fecha en la que se realizó el movimiento."
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_MOVIMIENTO_CHOICES,
        help_text="Si es un ingreso o un egreso."
    )
    cuenta = models.ForeignKey(
        CuentaFinanciera,
        on_delete=models.PROTECT,
        related_name="movimientos",
        help_text="Cuenta por donde entra o sale el dinero."
    )
    categoria = models.ForeignKey(
        CategoriaMovimiento,
        on_delete=models.PROTECT,
        related_name="movimientos",
        help_text="Categoría del movimiento (diezmo, ofrenda, sueldo, etc.)."
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Monto del movimiento."
    )
    descripcion = models.CharField(
        max_length=255,
        blank=True,
        help_text="Descripción breve o nota del movimiento."
    )
    referencia = models.CharField(
        max_length=100,
        blank=True,
        help_text="Referencia opcional (nº recibo, nº factura, etc.)."
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_registrados",
        help_text="Usuario que registró el movimiento."
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Movimiento financiero"
        verbose_name_plural = "Movimientos financieros"
        ordering = ["-fecha", "-creado_en"]

    def __str__(self):
        signo = "+" if self.tipo == "ingreso" else "-"
        return f"{self.fecha} · {self.categoria} · {signo}{self.monto}"
