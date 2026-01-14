from datetime import date
from django.db import models
from core.utils_config import get_edad_minima_miembro_oficial
from django.core.validators import RegexValidator
from django.db.models import Max
from core.models import ConfiguracionSistema
from django.conf import settings



ETAPA_ACTUAL_CHOICES = [
    ("miembro", "Miembro"),
    ("nuevo_creyente", "Nuevo creyente"),
    ("reincorporado", "Reincorporado"),
    ("inactivo", "Inactivo"),
]

ESTADO_PASTORAL_REINGRESO_CHOICES = [
    ("reconciliado", "Reconciliado"),
    ("integrado", "Integrado (viene de otra iglesia)"),
    ("observacion", "En observación"),
    
]


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
    ("trasladado", "Trasladado"),
]

CATEGORIA_EDAD_CHOICES = [
    ("infante", "Infante"),
    ("nino", "Niño"),
    ("adolescente", "Adolescente"),
    ("joven", "Jóven"),
    ("adulto", "Adulto"),
    ("adulto_mayor", "Adulto mayor"),
]
VIVIENDA_CHOICES = [
    ("propia", "Casa propia"),
    ("alquilada", "Alquilada"),
    ("familiar", "En casa de familiares"),
    ("prestada", "Prestada / Cedida"),
]

VEHICULO_TIPO_CHOICES = [
    ("carro", "Carro"),
    ("jeepeta", "Jeepeta"),
    ("camioneta", "Camioneta"),
    ("motor", "Motor"),
    ("camion", "Camión"),
    ("otro", "Otro"),
]

SITUACION_ECONOMICA_CHOICES = [
    ("estable", "Estable"),
    ("vulnerable", "Vulnerable"),
    ("critica", "Crítica"),
]


class RazonSalidaMiembro(models.Model):



    APLICA_A_CHOICES = [
        ("miembro", "Miembro"),
        ("nuevo_creyente", "Nuevo creyente"),
        ("ambos", "Ambos"),
    ]

    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    
    ESTADO_RESULTANTE_CHOICES = [
    ("", "—"),
    ("descarriado", "Descarriado"),
    ("trasladado", "Trasladado"),
    ]

    estado_resultante = models.CharField(
        max_length=20,
        choices=ESTADO_RESULTANTE_CHOICES,
        blank=True,
        default="",
        help_text="Al dar salida, este será el estado_miembro que quedará marcado (ej: descarriado/trasladado).",
    )

    permite_carta = models.BooleanField(
        default=False,
        help_text="Permite generar/enviar carta de salida (ej: Trasladado, Otra iglesia)."
    )

    aplica_a = models.CharField(
        max_length=20,
        choices=APLICA_A_CHOICES,
        default="ambos",
        help_text="Define si esta razón aplica a miembros, nuevos creyentes o ambos.",
    )

    class Meta:
        verbose_name = "Razón de salida"
        verbose_name_plural = "Razones de salida"
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

    # --- Identificación personal ---
    cedula_validator = RegexValidator(
        regex=r"^\d{3}-\d{7}-\d$",
        message="La cédula debe tener el formato 000-0000000-0",
    )

    cedula = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[cedula_validator],
        help_text="Formato: 000-0000000-0",
    )

    pasaporte = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Número de pasaporte del miembro.",
        )
    # -------------------------
    # REINGRESO / REINCORPORACIÓN
    # -------------------------
    etapa_actual = models.CharField(
        max_length=20,
        choices=ETAPA_ACTUAL_CHOICES,
        default="miembro",
        db_index=True,
    )

    estado_pastoral_reingreso = models.CharField(
        max_length=20,
        choices=ESTADO_PASTORAL_REINGRESO_CHOICES,
        null=True,
        blank=True,
    )

    fecha_reingreso = models.DateField(
        null=True,
        blank=True,
    )

    origen_reingreso = models.CharField(
        max_length=20,
        choices=[
            ("descarriado", "Descarriado"),
            ("traslado", "Traslado"),
            ("pausa", "Pausa voluntaria"),
        ],
        null=True,
        blank=True,
    )

    carta_traslado_recibida = models.BooleanField(default=False)
    nota_pastoral_reingreso = models.TextField(blank=True)
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

    # --- Seguimiento espiritual básico ---
    nuevo_creyente = models.BooleanField(
        default=False,
        help_text="Marcar si es un nuevo creyente en proceso de seguimiento (aún no miembro oficial).",
    )
    # --- Usuario del sistema ---
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="miembro",
        help_text="Usuario del sistema vinculado a este miembro (si aplica)."
    )

    # --- Información laboral ---
    empleador = models.CharField(max_length=150, blank=True)
    puesto = models.CharField(max_length=100, blank=True)
    telefono_trabajo = models.CharField(max_length=20, blank=True)
    direccion_trabajo = models.TextField(blank=True)
    # --- Información socioeconómica (privada) ---
    tipo_vivienda = models.CharField(
        max_length=20,
        choices=VIVIENDA_CHOICES,
        blank=True,
        help_text="Tipo de vivienda donde reside el miembro.",
    )

    situacion_economica = models.CharField(
        max_length=20,
        choices=SITUACION_ECONOMICA_CHOICES,
        blank=True,
        help_text="Evaluación general (uso interno/pastoral).",
    )

    tiene_vehiculo = models.BooleanField(
        default=False,
        help_text="Marcar si el miembro posee vehículo.",
    )

    vehiculo_tipo = models.CharField(
        max_length=20,
        choices=VEHICULO_TIPO_CHOICES,
        blank=True,
        help_text="Tipo de vehículo (si aplica).",
    )

    vehiculo_marca = models.CharField(
        max_length=50,
        blank=True,
        help_text="Marca del vehículo (si aplica).",
    )

    vehiculo_placa = models.CharField(
        max_length=20,
        blank=True,
        help_text="Placa (si aplica).",
    )

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

    # Código interno de seguimiento para nuevos creyentes
    numero_seguimiento = models.PositiveIntegerField(
        null=True,
        blank=True,
        unique=True,
    )

    codigo_seguimiento = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=True,
)

    mentor = models.CharField(max_length=150, blank=True)
    lider_celula = models.CharField(max_length=150, blank=True)

    # --- Código único del miembro ---
    numero_miembro = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Número interno autogenerado para el miembro."
    )

    codigo_miembro = models.CharField(
        max_length=50,
        unique=True,
        null=True,      # 👈 importante: permite null para no chocar en la migración
        blank=True,
        help_text="Código final del miembro con prefijo, ej: TF-0001."
    )

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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cedula"],
                name="unique_cedula_miembro",
                condition=models.Q(cedula__isnull=False),
            )
        ]
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

        # Mantén tu lógica existente (edad, etc.)
        self.actualizar_categoria_edad()

        # ======================================
        # 1) NUEVOS CREYENTES → NC-XXXX
        # ======================================
        if self.nuevo_creyente:

            if self.numero_seguimiento is None:
                ultimo = Miembro.objects.aggregate(
                    Max("numero_seguimiento")
                )["numero_seguimiento__max"] or 0

                self.numero_seguimiento = ultimo + 1
                self.codigo_seguimiento = f"NC-{self.numero_seguimiento:04d}"

            # Asegurar que NO tenga código oficial
            self.numero_miembro = None
            self.codigo_miembro = None

        # ======================================
        # 2) MIEMBRO OFICIAL → TF-XXXX
        # ======================================
        else:

            cfg = ConfiguracionSistema.load()
            prefijo = cfg.codigo_miembro_prefijo or "TF-"


            if self.numero_miembro is None:
                ultimo = Miembro.objects.aggregate(
                    Max("numero_miembro")
                )["numero_miembro__max"] or 0

                self.numero_miembro = ultimo + 1
                self.codigo_miembro = f"{prefijo}{self.numero_miembro:04d}"

            # Limpiar seguimiento
            self.numero_seguimiento = None
            self.codigo_seguimiento = None



        super().save(*args, **kwargs)



    @property
    def es_miembro_oficial(self):
        """
        Un miembro oficial es:
        - Bautizado confirmado
        - Y con edad >= edad mínima configurada
        """
        edad = self.calcular_edad()
        if edad is None:
            return False
        edad_minima = get_edad_minima_miembro_oficial()
        return self.bautizado_confirmado and edad >= edad_minima

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
    # ✅ Tipos (guardamos CLAVES neutras y mostramos bonito según género)
    TIPO_RELACION_CHOICES = [
        # Núcleo
        ("padre", "Padre"),
        ("madre", "Madre"),
        ("hijo", "Hijo/a"),
        ("conyuge", "Cónyuge"),
        ("hermano", "Hermano/a"),

        # Familia extendida
        ("abuelo", "Abuelo/Abuela"),
        ("nieto", "Nieto/Nieta"),
        ("tio", "Tío/Tía"),
        ("sobrino", "Sobrino/Sobrina"),
        ("primo", "Primo/Prima"),

        # Familia política
        ("suegro", "Suegro/Suegra"),
        ("yerno", "Yerno/Nuera"),
        ("cunado", "Cuñado/Cuñada"),

        # Otros
        ("tutor", "Tutor/a"),
        ("otro", "Otro"),
    ]

    # ⬅️ Inversa base (cuando NO depende del género)
    RELACION_INVERSA_BASE = {
        "padre": "hijo",
        "madre": "hijo",
        "hijo": "padre",       # ⚠️ se ajusta por género en inverse_tipo()
        "conyuge": "conyuge",
        "hermano": "hermano",

        "abuelo": "nieto",
        "nieto": "abuelo",
        "tio": "sobrino",
        "sobrino": "tio",
        "primo": "primo",

        "suegro": "yerno",     # ⚠️ se ajusta por género en inverse_tipo()
        "yerno": "suegro",
        "cunado": "cunado",

        "tutor": "tutelado",   # opcional si quieres; si no, lo dejamos como "otro"
        "otro": "otro",
    }

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
    vive_junto = models.BooleanField(default=False, help_text="Marcar si viven en la misma casa.")
    es_responsable = models.BooleanField(default=False, help_text="Marcar si es responsable principal (económico / tutor).")
    notas = models.TextField(blank=True, help_text="Notas breves sobre la relación familiar (opcional).")

    class Meta:
        verbose_name = "Relación familiar"
        verbose_name_plural = "Relaciones familiares"

    def __str__(self):
        return f"{self.miembro} - {self.get_tipo_relacion_display()} de {self.familiar}"

    # =========================
    # ✅ Helpers inteligentes
    # =========================
    @staticmethod
    def _norm_genero(g):
        g = (g or "").strip().lower()
        if g in ("m", "masculino", "hombre"):
            return "m"
        if g in ("f", "femenino", "mujer"):
            return "f"
        return ""

    @classmethod
    def label_por_genero(cls, tipo, genero):
        """
        Devuelve la etiqueta bonita (Hermano/Hermana, Tío/Tía, etc.)
        usando el género de la PERSONA que tiene ese rol.
        """
        genero = cls._norm_genero(genero)

        etiquetas = {
            "padre": ("Padre", "Padre"),
            "madre": ("Madre", "Madre"),
            "hijo": ("Hijo", "Hija"),
            "conyuge": ("Cónyuge", "Cónyuge"),  # si quieres: ("Esposo","Esposa")
            "hermano": ("Hermano", "Hermana"),

            "abuelo": ("Abuelo", "Abuela"),
            "nieto": ("Nieto", "Nieta"),
            "tio": ("Tío", "Tía"),
            "sobrino": ("Sobrino", "Sobrina"),
            "primo": ("Primo", "Prima"),

            "suegro": ("Suegro", "Suegra"),
            "yerno": ("Yerno", "Nuera"),
            "cunado": ("Cuñado", "Cuñada"),

            "tutor": ("Tutor", "Tutora"),
            "otro": ("Otro", "Otro"),
        }

        masc, fem = etiquetas.get(tipo, ("Otro", "Otro"))
        if genero == "f":
            return fem
        return masc

    @classmethod
    def inverse_tipo(cls, tipo, genero_persona_invertida=None):
        """
        Devuelve el tipo inverso.
        Ej:
          - si A es hijo de B -> B es padre/madre de A (depende del género de B)
          - si A es suegro de B -> B es yerno/nuera de A (depende del género de B)
        """
        base = cls.RELACION_INVERSA_BASE.get(tipo, "otro")

        # Ajustes por género
        gen = cls._norm_genero(genero_persona_invertida)

        if tipo == "hijo":
            # Si A dice: "B es mi hijo"
            # inversa: "yo soy padre/madre de B" => depende del género de "yo" (persona invertida)
            return "madre" if gen == "f" else "padre"

        if tipo == "suegro":
            # Si A dice: "B es mi suegro/suegra"
            # inversa: "yo soy yerno/nuera de B" => depende del género de "yo"
            return "yerno"  # la etiqueta bonita se resuelve por género al mostrar

        return base
