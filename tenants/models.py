
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

class TenantAwareModel(models.Model):
    """
    Clase base abstracta para modelos multi-tenant.
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True