from django.db import models
from django.conf import settings


class CuentaFinanciera(models.Model):
    TIPO_CUENTA_CHOICES = [
        ("caja", "Caja"),
        ("banco", "Banco"),
        ("otra", "Otra"),
    ]

    MONEDA_CHOICES = [
        ("DOP", "Pesos dominicanos"),
        ("USD", "Dólares estadounidenses"),
        ("EUR", "Euros"),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CUENTA_CHOICES,
        help_text="Tipo de cuenta (caja, banco, otra)."
    )
    moneda = models.CharField(
        max_length=10,
        choices=MONEDA_CHOICES,
        default="DOP",
        help_text="Moneda principal de la cuenta."
    )
    descripcion = models.CharField(
        max_length=255,
        blank=True,
        help_text="Descripción opcional de la cuenta."
    )
    saldo_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Saldo inicial de la cuenta."
    )
    esta_activa = models.BooleanField(
        default=True,
        help_text="Indica si la cuenta está activa."
    )

    class Meta:
        verbose_name = "Cuenta financiera"
        verbose_name_plural = "Cuentas financieras"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.moneda})"

class CategoriaMovimiento(models.Model):
    """
    Categorías para clasificar ingresos y egresos.
    Ejemplo ingreso: Diezmo, Ofrenda, Donación, Venta, Actividad.
    Ejemplo egreso: Pago sonido, Material limpieza, Honorarios, Construcción.
    """
    TIPO_CHOICES = [
        ("ingreso", "Ingreso"),
        ("egreso", "Egreso"),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        help_text="Si la categoría es de ingreso o de egreso."
    )
    descripcion = models.CharField(
        max_length=255,
        blank=True,
        help_text="Descripción opcional de la categoría."
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si la categoría está disponible para usar."
    )
    es_editable = models.BooleanField(
        default=True,
        help_text="Si la categoría puede ser editada/borrada desde el sistema."
    )

    class Meta:
        verbose_name = "Categoría de movimiento"
        verbose_name_plural = "Categorías de movimiento"
        ordering = ["tipo", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"


class MovimientoFinanciero(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [
        ("ingreso", "Ingreso"),
        ("egreso", "Egreso"),
    ]

    ORIGEN_INGRESO_CHOICES = [
        ("culto", "Culto / servicio"),
        ("actividad", "Actividad o evento"),
        ("donacion", "Donación individual"),
        ("venta", "Venta / recaudación"),
        ("ofrenda_especial", "Ofrenda especial"),
        ("otro", "Otro"),
    ]

    FORMA_PAGO_CHOICES = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia bancaria"),
        ("tarjeta", "Tarjeta"),
        ("cheque", "Cheque"),
        ("deposito", "Depósito bancario"),
        ("otro", "Otro"),
    ]

    ESTADO_MOVIMIENTO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("confirmado", "Confirmado"),
        ("cuadrado", "Cuadrado"),
        ("anulado", "Anulado"),
    ]

    # --- DATOS BÁSICOS ---
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
        help_text="Referencia opcional (nº recibo, nº factura, nº transferencia, etc.)."
    )

    # --- ORIGEN DEL INGRESO / EGRESO ---
    origen = models.CharField(
        max_length=30,
        choices=ORIGEN_INGRESO_CHOICES,
        blank=True,
        help_text="Origen principal del movimiento (culto, actividad, donación, etc.)."
    )
    servicio = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nombre del culto o servicio. Ej: Domingo AM, Jueves enseñanza."
    )
    evento = models.CharField(
        max_length=150,
        blank=True,
        help_text="Nombre del evento o actividad. Ej: Noche de tacos, Campamento juvenil."
    )
    persona_asociada = models.CharField(
        max_length=150,
        blank=True,
        help_text="Nombre de la persona asociada al ingreso (si aplica)."
    )
    ministerio = models.CharField(
        max_length=150,
        blank=True,
        help_text="Ministerio o departamento responsable. Ej: Jóvenes, Damas, Adolescentes."
    )
    cantidad_sobres = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cantidad de sobres recibidos (si aplica)."
    )

    # --- FORMA DE PAGO / ESTADO ---
    forma_pago = models.CharField(
        max_length=20,
        choices=FORMA_PAGO_CHOICES,
        blank=True,
        help_text="Forma de pago utilizada."
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_MOVIMIENTO_CHOICES,
        default="confirmado",
        help_text="Estado interno del movimiento."
    )

    # --- TRAZABILIDAD ---
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
