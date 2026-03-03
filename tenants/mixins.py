from django.db import models
from .managers import TenantManager

class TenantAwareModel(models.Model):
    """
    Hereda esto en tus modelos para incluir tenant + filtrado automático.
    """
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, db_index=True)

    objects = TenantManager()       # filtra automático por tenant del request
    all_objects = models.Manager()  # sin filtro (solo para admin/soporte)

    class Meta:
        abstract = True