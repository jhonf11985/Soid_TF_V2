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


class ConfiguracionSistema(models.Model):
    """
    Parámetros globales del sistema.
    Usamos un único registro (pk=1) como 'singleton'.
    """
    nombre_iglesia = models.CharField(
        "Nombre de la iglesia",
        max_length=150,
        default="Iglesia Torre Fuerte",
    )
    email_oficial = models.EmailField(
        "Correo oficial",
        blank=True
    )
    telefono_oficial = models.CharField(
        "Teléfono oficial",
        max_length=50,
        blank=True
    )
    direccion = models.TextField(
        "Dirección",
        blank=True
    )
    logo = models.ImageField(
        "Logo principal",
        upload_to="configuracion/",
        blank=True,
        null=True
    )
    edad_minima_miembro_oficial = models.PositiveIntegerField(
        "Edad mínima miembro oficial",
        default=12,
        help_text="Años para considerar a alguien miembro oficial / bautizable."
    )
    whatsapp_oficial = models.CharField(
        "WhatsApp oficial",
        max_length=50,
        blank=True,
        help_text="Solo números con código de país, sin espacios ni guiones."
    )
    pie_cartas = models.TextField(
        "Texto de pie de cartas",
        blank=True,
        help_text="Se puede usar al final de las cartas automáticas."
    )

    class Meta:
        verbose_name = "Configuración del sistema"
        verbose_name_plural = "Configuración del sistema"

    def __str__(self):
        return "Configuración del sistema"

    def save(self, *args, **kwargs):
        # Forzamos que siempre sea el registro 1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """
        Devuelve la configuración única (la crea si no existe).
        """
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                "nombre_iglesia": "Iglesia Torre Fuerte",
            }
        )
        return obj