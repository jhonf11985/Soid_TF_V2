from django.db import models
from django.utils.text import slugify


class EtiquetaDocumento(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    color = models.CharField(max_length=20, blank=True, default="#6b7280")
    activa = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Etiqueta"
        verbose_name_plural = "Etiquetas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre) if self.nombre else "etiqueta"
            slug = base_slug
            contador = 1

            while EtiquetaDocumento.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                contador += 1
                slug = f"{base_slug}-{contador}"

            self.slug = slug

        super().save(*args, **kwargs)