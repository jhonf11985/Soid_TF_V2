from django.conf import settings
from django.db import models


class TipoUnidad(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    orden = models.PositiveIntegerField(default=10)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tipo de unidad"
        verbose_name_plural = "Tipos de unidad"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class RolUnidad(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    es_liderazgo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=10)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Unidad(models.Model):
    # ─────────────────────────────────────────────────────────────
    # Choices
    # ─────────────────────────────────────────────────────────────
    CATEGORIA_CHOICES = [
        ("liderazgo", "Liderazgo"),
        ("evangelismo", "Evangelismo"),
        ("servicio", "Servicio"),
        ("adoracion", "Adoración"),
        ("conexion", "Conexión"),
    ]

    TIPO_ESTRUCTURA_CHOICES = [
        ("grupo", "Grupo"),
        ("departamento", "Departamento"),
        ("ministerio", "Ministerio"),
        ("celula", "Célula"),
        ("equipo", "Equipo"),
        ("comision", "Comisión"),
        ("otro", "Otro"),
    ]

    # ─────────────────────────────────────────────────────────────
    # Identidad
    # ─────────────────────────────────────────────────────────────
    nombre = models.CharField(max_length=120)

    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default="servicio",
    )

    tipo_estructura = models.CharField(
        max_length=20,
        choices=TIPO_ESTRUCTURA_CHOICES,
        default="ministerio",
    )

    tipo = models.ForeignKey(TipoUnidad, on_delete=models.PROTECT, related_name="unidades")
    padre = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="hijas")

    descripcion = models.TextField(blank=True)

    # ─────────────────────────────────────────────────────────────
    # Organización
    # ─────────────────────────────────────────────────────────────
    codigo = models.CharField(max_length=30, blank=True, default="")
    orden = models.PositiveIntegerField(default=10)
    visible = models.BooleanField(default=True)

    # ─────────────────────────────────────────────────────────────
    # Control / ciclo de vida
    # ─────────────────────────────────────────────────────────────
    activa = models.BooleanField(default=True)

    fecha_cierre = models.DateField(null=True, blank=True)
    motivo_cierre = models.CharField(max_length=180, blank=True, default="")
    notas = models.TextField(blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Unidad"
        verbose_name_plural = "Unidades"
        ordering = ["orden", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["tipo", "nombre", "padre"], name="uniq_unidad_por_tipo_nombre_padre")
        ]
        indexes = [
            models.Index(fields=["activa", "visible"]),
            models.Index(fields=["tipo_estructura", "categoria"]),
            models.Index(fields=["padre"]),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"

    def ruta(self):
        parts = [self.nombre]
        p = self.padre
        while p:
            parts.append(p.nombre)
            p = p.padre
        return " / ".join(reversed(parts))


# ✅ AJUSTA ESTO si tu modelo no se llama Miembro o no está en miembros_app
# Por defecto, asumimos: miembros_app.Miembro
class UnidadMembresia(models.Model):
    miembo_fk = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.PROTECT,
        related_name="membresias_unidad",
    )
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name="membresias")

    fecha_ingreso = models.DateField(null=True, blank=True)
    fecha_salida = models.DateField(null=True, blank=True)

    # Opcional pero útil
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
