
from django.db import models

class Tenant(models.Model):
    nombre = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)  # ej: torre-fuerte-higuey
    dominio = models.CharField(
        max_length=255,
        unique=True,
        help_text="Dominio o host exacto. Ej: higuey.soidtf.com o cliente1.com"
    )
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.dominio})"