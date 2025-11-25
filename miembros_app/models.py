from datetime import date
from django.db import models


GENERO_CHOICES = [
    ("masculino", "Masculino"),
    ("femenino", "Femenino"),
]


ESTADO_MIEMBRO_CHOICES = [
    ("activo", "Activo"),
    ("pasivo", "Pasivo"),
    ("observacion", "En observación"),
    ("disciplina", "En disciplina"),
    ("descarriado", "Descarriado"),
    ("catecumeno", "Catecúmeno"),
]

CATEGORIA_EDAD_CHOICES = [
    ("infante", "Infante"),
    ("nino", "Niño"),
    ("adolescente", "Adolescente"),
    ("joven", "Jóven"),
    ("adulto", "Adulto"),
    ("adulto_mayor", "Adulto mayor"),
]


class RazonSalidaMiembro(models.Model):
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre corto de la razón de salida (Traslado, Distancia, etc.).",
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción opcional de la razón.",
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si se desmarca, deja de aparecer en el selector, pero se mantiene el histórico.",
    )
    orden = models.PositiveIntegerField(
        default=0,
        help_text="Permite ordenar las razones en el selector.",
    )

    class Meta:
        verbose_name = "Razón de salida de miembro"
        verbose_name_plural = "Razones de salida de miembros"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Miembro(models.Model):
    # --- Información personal básica ---
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    genero = models.CharField(
        max_length=20,
        choices=GENERO_CHOICES,
        blank=True,
    )

    fecha_nacimiento = models.DateField(
        blank=True,
        null=True,
        help_text="Se usará para calcular la edad y clasificar la categoría.",
    )
    lugar_nacimiento = models.CharField(max_length=255, blank=True)
    nacionalidad = models.CharField(max_length=100, blank=True)

    estado_civil = models.CharField(max_length=20, blank=True)
    nivel_educativo = models.CharField(max_length=50, blank=True)
    profesion = models.CharField(max_length=100, blank=True)

    # --- Información de contacto ---
    telefono = models.CharField(max_length=20, blank=True)
    telefono_secundario = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    direccion = models.TextField(blank=True)
    sector = models.CharField(max_length=100, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    provincia = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=20, blank=True)

    # --- Contacto de emergencia y salud ---
    contacto_emergencia_nombre = models.CharField(max_length=150, blank=True)
    contacto_emergencia_telefono = models.CharField(max_length=20, blank=True)
    contacto_emergencia_relacion = models.CharField(max_length=50, blank=True)

    tipo_sangre = models.CharField(max_length=10, blank=True)
    alergias = models.TextField(blank=True)
    condiciones_medicas = models.TextField(blank=True)
    medicamentos = models.TextField(blank=True)

    # --- Información laboral ---
    empleador = models.CharField(max_length=150, blank=True)
    puesto = models.CharField(max_length=100, blank=True)
    telefono_trabajo = models.CharField(max_length=20, blank=True)
    direccion_trabajo = models.TextField(blank=True)

    # --- Información de membresía ---
    estado_miembro = models.CharField(
        max_length=20,
        choices=ESTADO_MIEMBRO_CHOICES,
        blank=True,
        help_text="Estado pastoral del miembro (activo, pasivo, etc.)",
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si está desmarcado, el miembro ya no pertenece a la iglesia Torre Fuerte.",
    )
    fecha_ingreso_iglesia = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha en que empezó a congregarse en la iglesia.",
    )
    es_trasladado = models.BooleanField(
        default=False,
        help_text="Marcar si el miembro viene trasladado de otra iglesia.",
    )
    iglesia_anterior = models.CharField(max_length=150, blank=True)

    fecha_conversion = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha aproximada de conversión, si se conoce.",
    )
    fecha_bautismo = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha de bautismo en agua.",
    )
    bautizado_confirmado = models.BooleanField(
        default=False,
        help_text="Marcar si se ha confirmado el bautismo del miembro.",
    )

    # --- Información de salida de la iglesia ---
    razon_salida = models.ForeignKey(
        "RazonSalidaMiembro",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="miembros",
        help_text="Motivo principal por el que ya no pertenece a la iglesia.",
    )
    fecha_salida = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha en que dejó de pertenecer a la iglesia Torre Fuerte.",
    )
    comentario_salida = models.TextField(
        blank=True,
        help_text="Comentarios adicionales sobre la salida (opcional).",
    )

    categoria_miembro = models.CharField(
        max_length=50,
        blank=True,
        help_text="Categoría pastoral del miembro (Miembro, Líder, Servidor, etc.)",
    )

    mentor = models.CharField(max_length=150, blank=True)
    lider_celula = models.CharField(max_length=150, blank=True)

    # --- Intereses y habilidades ---
    intereses = models.TextField(
        blank=True,
        help_text="Intereses generales (ministerios, áreas de servicio, etc.)",
    )
    habilidades = models.TextField(
        blank=True,
        help_text="Habilidades específicas (música, docencia, administración, etc.)",
    )
    otros_intereses = models.TextField(
        blank=True,
        help_text="Otros intereses no contemplados arriba.",
    )
    otras_habilidades = models.TextField(
        blank=True,
        help_text="Otras habilidades no contempladas arriba.",
    )

    # --- Información de clasificación automática ---
    categoria_edad = models.CharField(
        max_length=20,
        choices=CATEGORIA_EDAD_CHOICES,
        blank=True,
        help_text="Clasificación automática según la edad.",
    )

    # --- Fotografía y notas ---
    foto = models.ImageField(
        upload_to="miembros_fotos/",
        blank=True,
        null=True,
    )
    notas = models.TextField(
        blank=True,
        help_text="Notas pastorales o información relevante.",
    )

    # --- Metadatos ---
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    # ==========================
    # LÓGICA DE EDAD Y CATEGORÍA
    # ==========================
    def calcular_edad(self):
        """
        Calcula la edad en años a partir de la fecha de nacimiento.
        Devuelve None si no hay fecha de nacimiento.
        """
        if not self.fecha_nacimiento:
            return None

        hoy = date.today()
        edad = hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
        return edad

    def actualizar_categoria_edad(self):
        """
        Actualiza la categoría de edad en función de la edad calculada.
        """
        edad = self.calcular_edad()
        if edad is None:
            self.categoria_edad = ""
            return

        if edad < 6:
            self.categoria_edad = "infante"
        elif 6 <= edad <= 11:
            self.categoria_edad = "nino"
        elif 12 <= edad <= 17:
            self.categoria_edad = "adolescente"
        elif 18 <= edad <= 30:
            self.categoria_edad = "joven"
        elif 31 <= edad <= 59:
            self.categoria_edad = "adulto"
        else:
            self.categoria_edad = "adulto_mayor"

    def save(self, *args, **kwargs):
        # Antes de guardar, actualizamos la categoría de edad
        self.actualizar_categoria_edad()
        super().save(*args, **kwargs)

    @property
    def es_miembro_oficial(self):
        """
        Un miembro oficial es:
        - Bautizado confirmado
        - Y con 12 años o más
        (Más adelante se puede hacer configurable).
        """
        edad = self.calcular_edad()
        if edad is None:
            return False
        return self.bautizado_confirmado and edad >= 12

    @property
    def edad(self):
        """Retorna la edad calculada según la fecha de nacimiento."""
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        edad = hoy.year - self.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day):
            edad -= 1
        return edad


class MiembroRelacion(models.Model):
    TIPO_RELACION_CHOICES = [
        ("padre", "Padre"),
        ("madre", "Madre"),
        ("hijo", "Hijo/a"),
        ("conyuge", "Cónyuge"),
        ("hermano", "Hermano/a"),
        ("otro", "Otro"),
    ]

    miembro = models.ForeignKey(
        Miembro,
        on_delete=models.CASCADE,
        related_name="relaciones",
        help_text="Miembro principal.",
    )
    familiar = models.ForeignKey(
        Miembro,
        on_delete=models.CASCADE,
        related_name="como_familiar_en",
        help_text="Miembro que es familiar del principal.",
    )
    tipo_relacion = models.CharField(
        max_length=20,
        choices=TIPO_RELACION_CHOICES,
    )
    vive_junto = models.BooleanField(
        default=False,
        help_text="Marcar si viven en la misma casa.",
    )
    es_responsable = models.BooleanField(
        default=False,
        help_text="Marcar si es responsable principal (económico / tutor).",
    )
    notas = models.TextField(
        blank=True,
        help_text="Notas breves sobre la relación familiar (opcional).",
    )

    class Meta:
        verbose_name = "Relación familiar"
        verbose_name_plural = "Relaciones familiares"

    def __str__(self):
        return f"{self.miembro} - {self.get_tipo_relacion_display()} de {self.familiar}"
