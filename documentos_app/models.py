import os

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from tenants.mixins import TenantAwareModel


def documento_upload_path(instance, filename):
    extension = filename.split(".")[-1] if "." in filename else ""
    nombre_base = os.path.splitext(filename)[0]
    carpeta_id = instance.carpeta.id if instance.carpeta_id else "sin_carpeta"

    tenant_id = getattr(instance, "tenant_id", None) or "sin_tenant"

    if extension:
        return f"documentos/{tenant_id}/{carpeta_id}/{nombre_base}.{extension}"
    return f"documentos/{tenant_id}/{carpeta_id}/{nombre_base}"


class Carpeta(TenantAwareModel):
    VISIBILIDAD_CHOICES = [
        ("privado", "Privado"),
        ("interno", "Interno"),
        ("lideres", "Solo líderes"),
        ("administracion", "Administración"),
    ]

    nombre = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, blank=True)
    descripcion = models.TextField(blank=True)

    carpeta_padre = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="subcarpetas",
        null=True,
        blank=True,
    )

    color = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Color opcional en HEX. Ej: #2563eb",
    )
    icono = models.CharField(
        max_length=50,
        blank=True,
        default="folder",
        help_text="Nombre del icono Material Icons",
    )

    visibilidad = models.CharField(
        max_length=20,
        choices=VISIBILIDAD_CHOICES,
        default="interno",
    )

    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_gestion_carpetas_propias",
    )

    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Carpeta"
        verbose_name_plural = "Carpetas"
        ordering = ["orden", "nombre"]
        unique_together = ("tenant", "carpeta_padre", "nombre")

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        base_slug = slugify(self.nombre) if self.nombre else "carpeta"
        slug = base_slug
        contador = 1

        while Carpeta.objects.exclude(pk=self.pk).filter(
            tenant=self.tenant,
            slug=slug,
        ).exists():
            contador += 1
            slug = f"{base_slug}-{contador}"

        self.slug = slug
        super().save(*args, **kwargs)

    @property
    def es_raiz(self):
        return self.carpeta_padre is None

    def ruta_completa(self):
        partes = [self.nombre]
        padre = self.carpeta_padre

        while padre:
            partes.insert(0, padre.nombre)
            padre = padre.carpeta_padre

        return " / ".join(partes)


class CategoriaDocumento(TenantAwareModel):
    nombre = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, blank=True)
    descripcion = models.TextField(blank=True)
    color = models.CharField(max_length=20, blank=True, default="")
    icono = models.CharField(max_length=50, blank=True, default="label")
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categoría de documento"
        verbose_name_plural = "Categorías de documentos"
        ordering = ["orden", "nombre"]
        unique_together = ("tenant", "nombre")
        indexes = [
            models.Index(fields=["tenant", "nombre"]),
            models.Index(fields=["tenant", "slug"]),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre) if self.nombre else "categoria"
            slug = base_slug
            contador = 1

            while CategoriaDocumento.objects.exclude(pk=self.pk).filter(
                tenant=self.tenant,
                slug=slug,
            ).exists():
                contador += 1
                slug = f"{base_slug}-{contador}"

            self.slug = slug

        super().save(*args, **kwargs)


class EtiquetaDocumento(TenantAwareModel):
    nombre = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, blank=True)
    color = models.CharField(max_length=20, blank=True, default="#6b7280")
    activa = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Etiqueta"
        verbose_name_plural = "Etiquetas"
        ordering = ["nombre"]
        unique_together = ("tenant", "nombre")
        indexes = [
            models.Index(fields=["tenant", "nombre"]),
            models.Index(fields=["tenant", "slug"]),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre) if self.nombre else "etiqueta"
            slug = base_slug
            contador = 1

            while EtiquetaDocumento.objects.exclude(pk=self.pk).filter(
                tenant=self.tenant,
                slug=slug,
            ).exists():
                contador += 1
                slug = f"{base_slug}-{contador}"

            self.slug = slug

        super().save(*args, **kwargs)


class Documento(TenantAwareModel):
    ESTADO_CHOICES = [
        ("borrador", "Borrador"),
        ("revision", "Pendiente de revisión"),
        ("aprobado", "Aprobado"),
        ("archivado", "Archivado"),
        ("vencido", "Vencido"),
    ]

    VISIBILIDAD_CHOICES = [
        ("privado", "Privado"),
        ("interno", "Interno"),
        ("lideres", "Solo líderes"),
        ("administracion", "Administración"),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    archivo = models.FileField(
        upload_to=documento_upload_path,
        blank=True,
        null=True,
    )

    carpeta = models.ForeignKey(
        "documentos_app.Carpeta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos",
    )

    categoria = models.ForeignKey(
        "documentos_app.CategoriaDocumento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos",
    )

    etiquetas = models.ManyToManyField(
        "documentos_app.EtiquetaDocumento",
        blank=True,
        related_name="documentos",
    )

    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_gestion_propios",
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_gestion_creados",
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="borrador",
    )

    visibilidad = models.CharField(
        max_length=20,
        choices=VISIBILIDAD_CHOICES,
        default="interno",
    )

    fecha_emision = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    es_oficial = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    eliminado = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ["-created_at", "titulo"]
        indexes = [
            models.Index(fields=["tenant", "titulo"]),
            models.Index(fields=["tenant", "estado"]),
            models.Index(fields=["tenant", "eliminado"]),
            models.Index(fields=["tenant", "created_at"]),
        ]

    def __str__(self):
        return self.titulo

    @property
    def nombre_archivo(self):
        if self.archivo:
            return os.path.basename(self.archivo.name)
        return ""

    @property
    def extension_archivo(self):
        if self.archivo and "." in self.archivo.name:
            return self.archivo.name.split(".")[-1].lower()
        return ""

    @property
    def tamaño_legible(self):
        if not self.archivo:
            return ""

        try:
            size = self.archivo.size
        except Exception:
            return ""

        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{round(size / 1024, 2)} KB"
        return f"{round(size / (1024 * 1024), 2)} MB"