from django.db import models
from django.conf import settings
from miembros_app.models import Miembro
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.core.exceptions import ValidationError
from decimal import Decimal

# Multi-tenant
from tenants.models import Tenant, TenantAwareModel


class CuentaFinanciera(TenantAwareModel):
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
        validators=[MinValueValidator(Decimal("0"))],
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
        constraints = [
            # 👈 CONSTRAINT: Nombre único POR TENANT
            models.UniqueConstraint(
                fields=["tenant", "nombre"],
                name="uq_cuenta_financiera_nombre_por_tenant"
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.moneda})"

    def clean(self):
        """Validaciones a nivel de modelo."""
        super().clean()
        # Validar saldo inicial no negativo
        if self.saldo_inicial is not None and self.saldo_inicial < 0:
            raise ValidationError({
                "saldo_inicial": "El saldo inicial no puede ser negativo."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class CasillaF001(models.Model):
    """
    Casillas oficiales del Informe F.001 (Concilio).
    Se crean por defecto (seed) pero se pueden editar/agregar desde Admin.
    """

    SECCION_CHOICES = [
        ("ingresos_iglesia", "Ingresos Generales de la Iglesia"),
        ("ingresos_ministerios", "Ingresos de los Ministerios"),
        ("egresos", "Egresos de la Iglesia"),
        ("envios_ministerios", "Envíos a Ministerios Nacionales"),
        ("aportes_especiales", "Aportes Especiales"),
    ]


    codigo = models.CharField(
        max_length=60,
        unique=True,
        help_text="Código interno estable. Ej: ING_DIEZMOS, MIN_FEMENIL, EGR_SERVICIOS"
    )
    nombre = models.CharField(
        max_length=120,
        help_text="Nombre visible en Admin. Ej: Diezmos, Ministerio Femenil, Agua/Luz/Teléfono"
    )
    seccion = models.CharField(
        max_length=30,
        choices=SECCION_CHOICES,
        help_text="Sección del F.001 donde aparece esta casilla."
    )
    orden = models.PositiveIntegerField(
        default=0,
        help_text="Orden de aparición (opcional)."
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si está activo para usarse en categorías."
    )

    class Meta:
        ordering = ["seccion", "orden", "nombre"]
        verbose_name = "Casilla F.001"
        verbose_name_plural = "Casillas F.001"

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

class CategoriaMovimiento(TenantAwareModel):
    """
    Categorías para clasificar ingresos y egresos.
    Ejemplo ingreso: Diezmo, Ofrenda, Donación, Venta, Actividad.
    Ejemplo egreso: Pago sonido, Material limpieza, Honorarios, Construcción.
    """
    TIPO_CHOICES = [
        ("ingreso", "Ingreso"),
        ("egreso", "Egreso"),
    ]

    codigo = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        help_text="Código interno estable. Ej: CAT_DIEZMO_NO_REGULAR. Recomendado."
    )

    casilla_f001 = models.ForeignKey(
        CasillaF001,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categorias",
        help_text="Opcional. Si se asigna, esta categoría alimenta el Informe F.001."
    )

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
        constraints = [
            # 👈 CONSTRAINT: Nombre único por tipo POR TENANT
            models.UniqueConstraint(
                fields=["tenant", "nombre", "tipo"],
                name="uq_categoria_nombre_tipo_por_tenant"
            ),
            # 👈 CONSTRAINT: Código único POR TENANT (si existe)
            models.UniqueConstraint(
                fields=["tenant", "codigo"],
                condition=Q(codigo__isnull=False) & ~Q(codigo=""),
                name="uq_categoria_codigo_por_tenant"
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"


class MovimientoFinanciero(TenantAwareModel):
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
    # --- ESTRUCTURA (opcional) ---
    unidad = models.ForeignKey(
        "estructura_app.Unidad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
        help_text="Unidad de Estructura asociada (si el módulo Estructura está activo)."
    )
    cuenta_por_pagar = models.ForeignKey(
            "CuentaPorPagar",
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="pagos",
            help_text="Si este egreso es un pago de CxP, referencia a la cuenta por pagar."
        )

    ESTADO_MOVIMIENTO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("confirmado", "Confirmado"),
        ("cuadrado", "Cuadrado"),   
        ("anulado", "Anulado"),
    ]
    # --- ANULACIÓN / AUDITORÍA ---
    motivo_anulacion = models.TextField(
        blank=True,
        help_text="Motivo o comentario de por qué se anuló el movimiento."
    )
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_anulados",
        help_text="Usuario que anuló el movimiento."
    )
    anulado_en = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora en que se anuló el movimiento."
    )

    # --- TRANSFERENCIAS ---
    es_transferencia = models.BooleanField(
        default=False,
        help_text="Indica si este movimiento es parte de una transferencia entre cuentas."
    )
    transferencia_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID compartido por ambos movimientos de una transferencia."
    )
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
        validators=[MinValueValidator(Decimal("0.01"))],  # 👈 VALIDADOR: Monto > 0
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
    persona_asociada = models.ForeignKey(
        Miembro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
        help_text="Miembro asociado al movimiento."
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
        permissions = [
            ("ver_dashboard_finanzas", "Puede ver el Dashboard de Finanzas"),
        ]

    def __str__(self):
        signo = "+" if self.tipo == "ingreso" else "-"
        return f"{self.fecha} · {self.categoria} · {signo}{self.monto}"

    def clean(self):
        """Validaciones a nivel de modelo."""
        super().clean()
        errors = {}

        # 1. Monto debe ser mayor a cero
        if self.monto is not None and self.monto <= 0:
            errors["monto"] = "El monto debe ser mayor a cero."

        # 2. Categoría debe coincidir con el tipo de movimiento
        if self.categoria_id and self.tipo:
            if hasattr(self, 'categoria') and self.categoria:
                if self.categoria.tipo != self.tipo:
                    errors["categoria"] = (
                        f"La categoría '{self.categoria.nombre}' es de tipo "
                        f"'{self.categoria.tipo}', pero el movimiento es de tipo '{self.tipo}'."
                    )

        # 3. Cuenta debe estar activa (solo para nuevos registros)
        if not self.pk and self.cuenta_id:
            if hasattr(self, 'cuenta') and self.cuenta and not self.cuenta.esta_activa:
                errors["cuenta"] = "No puedes registrar movimientos en una cuenta inactiva."

        # 4. Si está anulado, debe tener motivo
        if self.estado == "anulado" and not self.motivo_anulacion:
            errors["motivo_anulacion"] = "Debe indicar el motivo de anulación."

        if errors:
            raise ValidationError(errors)

    def get_transferencia_par(self):
        """
        Retorna el movimiento relacionado si este es una transferencia.
        """
        if not self.es_transferencia or not self.transferencia_id:
            return None
        
        # 👈 FILTRAR POR TENANT
        return MovimientoFinanciero.objects.filter(
            tenant=self.tenant,
            transferencia_id=self.transferencia_id
        ).exclude(pk=self.pk).first()


class AdjuntoMovimiento(models.Model):
    """
    Archivos adjuntos a movimientos financieros.
    Permite almacenar comprobantes, facturas, recibos, etc.
    """
    
    EXTENSIONES_PERMITIDAS = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'doc', 'docx', 'xls', 'xlsx']
    MAX_TAMAÑO_MB = 10  # 👈 Tamaño máximo en MB
    
    movimiento = models.ForeignKey(
        MovimientoFinanciero,
        on_delete=models.CASCADE,
        related_name="adjuntos",
        help_text="Movimiento al que pertenece este adjunto."
    )
    
    archivo = models.FileField(
        upload_to="finanzas/adjuntos/%Y/%m/",
        help_text="Archivo adjunto."
    )
    
    nombre_original = models.CharField(
        max_length=255,
        help_text="Nombre original del archivo."
    )
    
    tamaño = models.PositiveIntegerField(
        help_text="Tamaño del archivo en bytes."
    )
    
    tipo_mime = models.CharField(
        max_length=100,
        blank=True,
        help_text="Tipo MIME del archivo (image/jpeg, application/pdf, etc.)."
    )
    
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="adjuntos_subidos",
        help_text="Usuario que subió el archivo."
    )
    
    subido_en = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de subida."
    )
    
    class Meta:
        verbose_name = "Adjunto de movimiento"
        verbose_name_plural = "Adjuntos de movimientos"
        ordering = ["-subido_en"]
    
    def __str__(self):
        return f"{self.nombre_original} - {self.movimiento}"

    def clean(self):
        """Validaciones del adjunto."""
        super().clean()
        errors = {}

        # Validar extensión
        if self.nombre_original:
            extension = self.nombre_original.split('.')[-1].lower()
            if extension not in self.EXTENSIONES_PERMITIDAS:
                errors["archivo"] = (
                    f"Extensión '{extension}' no permitida. "
                    f"Use: {', '.join(self.EXTENSIONES_PERMITIDAS)}"
                )

        # Validar tamaño
        if self.tamaño and self.tamaño > (self.MAX_TAMAÑO_MB * 1024 * 1024):
            errors["archivo"] = f"El archivo excede el tamaño máximo de {self.MAX_TAMAÑO_MB}MB."

        if errors:
            raise ValidationError(errors)
    
    def get_icono(self):
        """
        Retorna el icono de Material Icons según el tipo de archivo.
        """
        extension = self.nombre_original.split('.')[-1].lower()
        
        iconos = {
            'pdf': 'picture_as_pdf',
            'doc': 'description',
            'docx': 'description',
            'xls': 'table_chart',
            'xlsx': 'table_chart',
            'csv': 'table_chart',
            'jpg': 'image',
            'jpeg': 'image',
            'png': 'image',
            'gif': 'image',
            'webp': 'image',
        }
        
        return iconos.get(extension, 'insert_drive_file')
    
    def es_imagen(self):
        """
        Retorna True si el archivo es una imagen.
        """
        extension = self.nombre_original.split('.')[-1].lower()
        return extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']
    
    def tamaño_formateado(self):
        """
        Retorna el tamaño del archivo en formato legible.
        """
        if self.tamaño < 1024:
            return f"{self.tamaño} B"
        elif self.tamaño < 1024 * 1024:
            return f"{self.tamaño / 1024:.1f} KB"
        else:
            return f"{self.tamaño / (1024 * 1024):.1f} MB"
    
    def puede_eliminar(self, usuario):
        """
        Verifica si un usuario puede eliminar este adjunto.
        """
        if usuario.is_staff or usuario.is_superuser:
            return True
        if self.subido_por == usuario:
            return True
        return False


# ==========================================================
# CUENTAS POR PAGAR (CxP) – MODELOS BASE
# ==========================================================
class ProveedorFinanciero(TenantAwareModel):
    """
    Proveedor / Beneficiario al que se le debe dinero.
    Puede ser persona o empresa. Se usa en Cuentas por Pagar (CxP).
    """

    TIPO_CHOICES = [
        ("persona", "Persona"),
        ("empresa", "Empresa"),
    ]

    TIPO_PROVEEDOR_CHOICES = [
        ("servicio", "Servicio"),
        ("consumibles", "Consumibles"),
        ("mixto", "Mixto"),
    ]

    TIPO_DOCUMENTO_CHOICES = [
        ("", "—"),
        ("cedula", "Cédula"),
        ("rnc", "RNC"),
        ("pasaporte", "Pasaporte"),
        ("otro", "Otro"),
    ]

    METODO_PAGO_CHOICES = [
        ("", "—"),
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia"),
        ("cheque", "Cheque"),
    ]

    TIPO_CUENTA_CHOICES = [
        ("", "—"),
        ("ahorros", "Ahorros"),
        ("corriente", "Corriente"),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="persona")
    tipo_proveedor = models.CharField(
        max_length=12,
        choices=TIPO_PROVEEDOR_CHOICES,
        default="servicio",
        help_text="Clasificación: servicio o consumibles."
    )

    nombre = models.CharField(max_length=150)

    miembro = models.ForeignKey(
        Miembro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proveedor_financiero",
        help_text="Si este proveedor coincide con un miembro, puedes enlazarlo (opcional)."
    )

    tipo_documento = models.CharField(
        max_length=15,
        choices=TIPO_DOCUMENTO_CHOICES,
        default="",
        blank=True
    )
    documento = models.CharField(
        max_length=25,
        null=True,
        blank=True,
        help_text="RNC/Cédula/Pasaporte. Guardar sin guiones (solo números cuando aplique)."
    )

    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)

    plazo_dias_pago = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(365)],
        help_text="Días de crédito para calcular vencimiento si la factura no trae fecha."
    )

    metodo_pago_preferido = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default="",
        blank=True
    )

    banco = models.CharField(max_length=80, blank=True)
    tipo_cuenta = models.CharField(
        max_length=15,
        choices=TIPO_CUENTA_CHOICES,
        default="",
        blank=True
    )
    numero_cuenta = models.CharField(
        max_length=34,
        blank=True,
        help_text="Número de cuenta (texto, puede incluir ceros iniciales)."
    )
    titular_cuenta = models.CharField(
        max_length=150,
        blank=True,
        help_text="Titular de la cuenta si difiere del proveedor (opcional)."
    )

    bloqueado = models.BooleanField(
        default=False,
        help_text="Si está bloqueado, no se deben permitir nuevas CxP para este proveedor."
    )
    notas = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proveedor financiero"
        verbose_name_plural = "Proveedores financieros"
        ordering = ["nombre"]
        constraints = [
            # 👈 CONSTRAINT: Documento único por tipo POR TENANT
            models.UniqueConstraint(
                fields=["tenant", "tipo_documento", "documento"],
                condition=Q(documento__isnull=False) & ~Q(documento=""),
                name="uq_proveedor_tipo_doc_documento_por_tenant",
            ),
            # 👈 CONSTRAINT: Nombre único POR TENANT
            models.UniqueConstraint(
                fields=["tenant", "nombre"],
                name="uq_proveedor_nombre_por_tenant"
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        """Validaciones del proveedor."""
        super().clean()
        errors = {}

        # Si tiene datos bancarios parciales, exigir completos
        tiene_banco = bool(self.banco)
        tiene_cuenta = bool(self.numero_cuenta)

        if tiene_banco and not tiene_cuenta:
            errors["numero_cuenta"] = "Si indica banco, debe completar el número de cuenta."
        if tiene_cuenta and not tiene_banco:
            errors["banco"] = "Si indica número de cuenta, debe completar el banco."

        # Si método es transferencia, exigir datos bancarios
        if self.metodo_pago_preferido == "transferencia":
            if not tiene_banco:
                errors["banco"] = "Para transferencia debe indicar el banco."
            if not tiene_cuenta:
                errors["numero_cuenta"] = "Para transferencia debe indicar el número de cuenta."

        if errors:
            raise ValidationError(errors)


class CuentaPorPagar(TenantAwareModel):
    """
    Representa una obligación pendiente.
    NO mueve caja. La caja se afecta cuando se cree el EGRESO (Paso de pagos).
    """
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("parcial", "Parcial"),
        ("pagada", "Pagada"),
        ("vencida", "Vencida"),
        ("cancelada", "Cancelada"),
    ]

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    proveedor = models.ForeignKey(
        ProveedorFinanciero,
        on_delete=models.PROTECT,
        related_name="cuentas_por_pagar"
    )

    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)

    categoria = models.ForeignKey(
        CategoriaMovimiento,
        on_delete=models.PROTECT,
        related_name="cxp",
        limit_choices_to={"tipo": "egreso"},
        help_text="Categoría de egreso para reportes (luz, alquiler, honorarios, etc.)."
    )

    cuenta_sugerida = models.ForeignKey(
        CuentaFinanciera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cxp_sugeridas",
        help_text="Cuenta desde la que normalmente se pagará (opcional)."
    )

    concepto = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    referencia = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nº factura, recibo, contrato, etc. (opcional)."
    )

    monto_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],  # 👈 VALIDADOR
    )
    monto_pagado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],  # 👈 VALIDADOR
    )

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente")

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cxp_creadas"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cuenta por pagar"
        verbose_name_plural = "Cuentas por pagar"
        ordering = ["-fecha_emision", "-creado_en"]
        indexes = [
            models.Index(fields=["estado", "fecha_vencimiento"]),
            models.Index(fields=["fecha_emision"]),
        ]

    def __str__(self):
        return f"{self.proveedor} · {self.concepto} · {self.monto_total}"

    @property
    def saldo_pendiente(self):
        return (self.monto_total or 0) - (self.monto_pagado or 0)

    def clean(self):
        """Validaciones de la CxP."""
        super().clean()
        errors = {}

        # 1. Monto total debe ser mayor a cero
        if self.monto_total is not None and self.monto_total <= 0:
            errors["monto_total"] = "El monto debe ser mayor a cero."

        # 2. Monto pagado no puede ser mayor al total
        if self.monto_pagado and self.monto_total:
            if self.monto_pagado > self.monto_total:
                errors["monto_pagado"] = "El monto pagado no puede superar el monto total."

        # 3. Fecha vencimiento no puede ser anterior a emisión
        if self.fecha_emision and self.fecha_vencimiento:
            if self.fecha_vencimiento < self.fecha_emision:
                errors["fecha_vencimiento"] = (
                    "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
                )

        # 4. No crear CxP para proveedor bloqueado (solo nuevos)
        if not self.pk and self.proveedor_id:
            if hasattr(self, 'proveedor') and self.proveedor and self.proveedor.bloqueado:
                errors["proveedor"] = (
                    f"El proveedor '{self.proveedor.nombre}' está bloqueado. "
                    "No se pueden crear nuevas cuentas por pagar."
                )

        if errors:
            raise ValidationError(errors)

    def actualizar_estado(self):
        """Actualiza el estado según el monto pagado."""
        from django.utils import timezone
        
        if self.monto_pagado >= self.monto_total:
            self.estado = "pagada"
        elif self.monto_pagado > 0:
            self.estado = "parcial"
        elif self.fecha_vencimiento and self.fecha_vencimiento < timezone.localdate():
            self.estado = "vencida"
        else:
            self.estado = "pendiente"