from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal

class ReporteUnidadCierre(models.Model):
    TIPO_CHOICES = (
        ("trimestre", "Trimestral"),
        ("anio", "Anual"),
    )

    unidad = models.ForeignKey("estructura_app.Unidad", on_delete=models.CASCADE, related_name="reportes_cierre")
    anio = models.PositiveIntegerField()
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES)

    # Solo aplica cuando tipo = "trimestre"
    trimestre = models.PositiveSmallIntegerField(null=True, blank=True)

    # Congelamos el resumen (snapshot)
    resumen = models.JSONField(default=dict, blank=True)

    # Texto del líder
    reflexion = models.TextField(blank=True, default="")
    necesidades = models.TextField(blank=True, default="")
    plan_proximo = models.TextField(blank=True, default="")

    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unidad", "anio", "tipo", "trimestre"],
                name="uniq_reporte_unidad_cierre"
            ),
        ]
        ordering = ["-anio", "-tipo", "-trimestre"]

    def __str__(self):
        if self.tipo == "anio":
            return f"{self.unidad} · Anual {self.anio}"
        return f"{self.unidad} · Trimestral Q{self.trimestre} {self.anio}"

class ActividadUnidad(models.Model):
    TIPO_REUNION = "REUNION"
    TIPO_SALIDA = "SALIDA"
    TIPO_VISITA = "VISITA"
    TIPO_EVENTO = "EVENTO"
    TIPO_OTRO = "OTRO"

    TIPOS = (
        (TIPO_REUNION, "Reunión"),
        (TIPO_SALIDA, "Salida"),
        (TIPO_VISITA, "Visita"),
        (TIPO_EVENTO, "Evento"),
        (TIPO_OTRO, "Otro"),
    )

    unidad = models.ForeignKey(
        "estructura_app.Unidad",
        on_delete=models.CASCADE,
        related_name="actividades",
    )

    fecha = models.DateField(default=timezone.localdate)
    titulo = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, choices=TIPOS, default=TIPO_OTRO)
    lugar = models.CharField(max_length=120, blank=True)

    responsable = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="actividades_responsable",
    )

    participantes = models.ManyToManyField(
        "miembros_app.Miembro",
        blank=True,
        related_name="actividades_participa",
    )

    # Para métricas específicas por tipo de unidad (Evangelismo, Jóvenes, etc.)
    # Ejemplo Evangelismo: {"alcanzados": 20, "nuevos_creyentes": 3, "seguimientos": 5}
    datos = models.JSONField(default=dict, blank=True)

    notas = models.TextField(blank=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actividades_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Actividad de unidad"
        verbose_name_plural = "Actividades de unidad"
        ordering = ["-fecha", "-creado_en"]
        indexes = [
            models.Index(fields=["unidad", "fecha"]),
            models.Index(fields=["unidad", "tipo"]),
        ]

    def __str__(self):
        return f"{self.titulo} ({self.unidad})"


class ReporteUnidadPeriodo(models.Model):
    unidad = models.ForeignKey(
        "estructura_app.Unidad",
        on_delete=models.CASCADE,
        related_name="reportes_periodo",
    )

    anio = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField()  # 1-12

    # Resumen calculado desde ActividadUnidad
    resumen = models.JSONField(default=dict, blank=True)

    # Parte humana/pastoral
    reflexion = models.TextField(blank=True)
    necesidades = models.TextField(blank=True)
    plan_proximo = models.TextField(blank=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_creados",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reporte por período"
        verbose_name_plural = "Reportes por período"
        ordering = ["-anio", "-mes", "unidad__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["unidad", "anio", "mes"],
                name="uniq_reporte_unidad_anio_mes",
            )
        ]
        indexes = [
            models.Index(fields=["unidad", "anio", "mes"]),
        ]

    def __str__(self):
        return f"Reporte {self.mes:02d}/{self.anio} - {self.unidad}"


class RolUnidad(models.Model):
    TIPO_LIDERAZGO = "LIDERAZGO"
    TIPO_PARTICIPACION = "PARTICIPACION"
    TIPO_TRABAJO = "TRABAJO"

    TIPOS = (
        (TIPO_LIDERAZGO, "Liderazgo"),
        (TIPO_PARTICIPACION, "Miembro (participación)"),
        (TIPO_TRABAJO, "Trabajo (servicio)"),
    )

    nombre = models.CharField(max_length=60, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default=TIPO_PARTICIPACION)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=10)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class TipoUnidad(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    icono = models.CharField(
        max_length=40,
        default="account_tree",
        help_text="Nombre del icono Material Icons (ej: groups, folder)"
    )
    orden = models.PositiveIntegerField(default=10)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tipo de unidad"
        verbose_name_plural = "Tipos de unidad"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre
class CategoriaUnidad(models.Model):
    codigo = models.SlugField(max_length=30, unique=True)
    nombre = models.CharField(max_length=60, unique=True)
    orden = models.PositiveIntegerField(default=10)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría de unidad"
        verbose_name_plural = "Categorías de unidad"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre




class Unidad(models.Model):
    nombre = models.CharField(max_length=120)

    categoria = models.ForeignKey(
        CategoriaUnidad,
        on_delete=models.PROTECT,
        related_name="unidades",
    )

    tipo = models.ForeignKey(
        TipoUnidad,
        on_delete=models.PROTECT,
        related_name="unidades",
    )

    padre = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hijas",
    )

    descripcion = models.TextField(blank=True)

    codigo = models.CharField(max_length=30, blank=True, default="")
    orden = models.PositiveIntegerField(default=10)
    visible = models.BooleanField(default=True)

    activa = models.BooleanField(default=True)
    fecha_cierre = models.DateField(null=True, blank=True)
    motivo_cierre = models.CharField(max_length=180, blank=True, default="")
    notas = models.TextField(blank=True)
    imagen = models.ImageField(upload_to="unidades/", null=True, blank=True)


    # ✅ RANGO DE EDAD (filtro estructural de la unidad)
    edad_min = models.PositiveIntegerField(null=True, blank=True)
    edad_max = models.PositiveIntegerField(null=True, blank=True)

      # 🔴🔴🔴 AQUÍ ESTÁ LO QUE FALTABA 🔴🔴🔴
    reglas = models.JSONField(
        default=dict,
        blank=True,
        help_text="Reglas de membresía, acceso y restricciones de la unidad"
    )


    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    @property
    def esta_bloqueada(self):
        return (
            self.membresias.filter(activo=True).exists()
            or self.cargos.filter(vigente=True).exists()
        )

    @property
    def ruta(self):
        partes = [self.nombre]
        padre = self.padre
        while padre:
            partes.append(padre.nombre)
            padre = padre.padre
        return " / ".join(reversed(partes))

    def __str__(self):
        return self.ruta

    class Meta:
        ordering = ["orden", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo", "nombre", "padre"],
                name="uniq_unidad_por_tipo_nombre_padre"
            )
        ]
        indexes = [
            models.Index(fields=["activa", "visible"]),
            models.Index(fields=["categoria"]),
            models.Index(fields=["padre"]),
        ]


class UnidadMembresia(models.Model):
    miembo_fk = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.PROTECT,
        related_name="membresias_unidad",
    )
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name="membresias")
    rol = models.ForeignKey(
        "estructura_app.RolUnidad",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="membresias",
    )

    fecha_ingreso = models.DateField(null=True, blank=True)
    fecha_salida = models.DateField(null=True, blank=True)

    tipo = models.CharField(
        max_length=20,
        choices=[
            ("miembro", "Miembro"),
            ("colaborador", "Colaborador"),
            ("invitado", "Invitado"),
        ],
        default="miembro",
    )

    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Membresía de unidad"
        verbose_name_plural = "Membresías de unidad"
        ordering = ["-activo", "unidad__nombre"]
        constraints = [
            models.UniqueConstraint(fields=["miembo_fk", "unidad"], name="uniq_miembro_unidad")
        ]

    def __str__(self):
        return f"{self.miembo_fk} -> {self.unidad}"


class UnidadCargo(models.Model):
    miembo_fk = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.PROTECT,
        related_name="cargos_unidad",
    )
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name="cargos")
    rol = models.ForeignKey(RolUnidad, on_delete=models.PROTECT, related_name="cargos")

    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    vigente = models.BooleanField(default=True)
    notas = models.TextField(blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cargo en unidad"
        verbose_name_plural = "Cargos en unidad"
        ordering = ["-vigente", "unidad__nombre", "rol__orden"]
        indexes = [
            models.Index(fields=["unidad", "vigente"]),
            models.Index(fields=["miembo_fk", "vigente"]),
        ]

    def __str__(self):
        return f"{self.rol} - {self.miembo_fk} ({self.unidad})"


class MovimientoUnidad(models.Model):
    TIPO_INGRESO = "INGRESO"
    TIPO_EGRESO = "EGRESO"

    TIPOS = (
        (TIPO_INGRESO, "Ingreso"),
        (TIPO_EGRESO, "Egreso"),
    )

    unidad = models.ForeignKey(
        "estructura_app.Unidad",
        on_delete=models.CASCADE,
        related_name="movimientos",
    )

    tipo = models.CharField(max_length=10, choices=TIPOS, default=TIPO_INGRESO)
    fecha = models.DateField(default=timezone.localdate)

    monto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    concepto = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True, default="")

    # Control
    anulado = models.BooleanField(default=False)
    motivo_anulacion = models.CharField(max_length=180, blank=True, default="")

    # 🔍 AUDITORÍA NIVEL 1
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_unidad_creados",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_unidad_actualizados",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(fields=["unidad", "fecha"]),
            models.Index(fields=["unidad", "tipo"]),
            models.Index(fields=["unidad", "anulado"]),
        ]

    def __str__(self):
        return f"{self.unidad} · {self.get_tipo_display()} · {self.fecha} · {self.monto}"

    
class MovimientoUnidadLog(models.Model):
    ACCION_CREAR = "CREAR"
    ACCION_EDITAR = "EDITAR"
    ACCION_ANULAR = "ANULAR"
    ACCIONES = (
        (ACCION_CREAR, "Crear"),
        (ACCION_EDITAR, "Editar"),
        (ACCION_ANULAR, "Anular"),
    )

    movimiento = models.ForeignKey(
        "MovimientoUnidad",
        on_delete=models.CASCADE,
        related_name="logs",
    )
    accion = models.CharField(max_length=10, choices=ACCIONES)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="movimientos_unidad_logs",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    # Solo guardamos lo relevante (porque solo editas fecha y concepto)
    fecha_antes = models.DateField(null=True, blank=True)
    fecha_despues = models.DateField(null=True, blank=True)

    concepto_antes = models.CharField(max_length=255, blank=True, default="")
    concepto_despues = models.CharField(max_length=255, blank=True, default="")

    # Extra opcional útil
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.movimiento_id} {self.accion} {self.creado_en:%Y-%m-%d %H:%M}"
