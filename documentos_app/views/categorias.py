from django.db import models
from django.utils.text import slugify


class CategoriaDocumento(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
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

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre) if self.nombre else "categoria"
            slug = base_slug
            contador = 1

            while CategoriaDocumento.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                contador += 1
                slug = f"{base_slug}-{contador}"

            self.slug = slug

        super().save(*args, **kwargs)