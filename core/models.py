from django.db import models


class Module(models.Model):
    """
    Representa un módulo del sistema (Miembros, Finanzas, etc.),
    similar a los módulos de Odoo.
    """
    name = models.CharField("Nombre visible", max_length=100)
    code = models.SlugField(
        "Código interno",
        max_length=50,
        unique=True,
        help_text="Ej: miembros, finanzas, discipulado"
    )
    description = models.TextField("Descripción corta", blank=True)
    icon = models.CharField(
        "Icono (opcional)",
        max_length=100,
        blank=True,
        help_text="Ej: fa-users, fa-church, etc."
    )
    color = models.CharField(
        "Color de tarjeta",
        max_length=20,
        default="#0097A7",
        help_text="Ej: #0097A7"
    )
    url_name = models.CharField(
        "Nombre de URL",
        max_length=100,
        help_text="El name de la ruta en urls.py"
    )
    is_enabled = models.BooleanField(
        "Módulo activo",
        default=True,
        help_text="Si está desmarcado, no aparece en la pantalla de inicio."
    )
    order = models.PositiveIntegerField(
        "Orden",
        default=0,
        help_text="Posición del módulo en el home."
    )

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"

    def __str__(self):
        return self.name
