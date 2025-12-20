from django.conf import settings
from django.db import models

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
