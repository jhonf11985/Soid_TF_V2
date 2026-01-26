from datetime import date
from django.db import models
from core.utils_config import get_edad_minima_miembro_oficial
from django.core.validators import RegexValidator
from django.db.models import Max
from core.models import ConfiguracionSistema
from django.conf import settings
from django.utils import timezone
import re
from django.db import transaction

# ==========================
# FORMACIÓN MINISTERIAL (CHOICES)
# ==========================

ROL_MINISTERIAL_CHOICES = [
    ("", "—"),
    ("pastor", "Pastor"),
    ("evangelista", "Evangelista"),
    ("misionero", "Misionero"),
    ("obrero", "Obrero"),
    ("diacono", "Diácono"),
    ("lider", "Líder"),
]

ESTADO_MINISTERIAL_CHOICES = [
    ("", "—"),
    ("activo", "Activo"),
    ("pausa", "En pausa"),
    ("retirado", "Retirado"),
]

NIVEL_FORMACION_CHOICES = [
    ("", "—"),
    ("basica", "Básica"),
    ("tecnica", "Técnica"),
    ("diplomado", "Diplomado"),
    ("licenciatura", "Licenciatura"),
    ("otro", "Otro"),
]

AREA_FORMACION_CHOICES = [
    ("", "—"),
    ("pastoral", "Pastoral"),
    ("biblica", "Bíblica"),
    ("misionologia", "Misionología"),
    ("consejeria", "Consejería"),
    ("educacion_cristiana", "Educación Cristiana"),
    ("otra", "Otra"),
]

TIPO_MISION_CHOICES = [
    ("", "—"),
    ("permanente", "Permanente"),
    ("temporal", "Temporal"),
    ("viajes", "Viajes misioneros"),
]

CIUDAD_CHOICES = [
    ("Higuey", "Higüey"),
    ("Punta Cana", "Punta Cana"),
    ("San Rafael del Yuma", "San Rafael del Yuma"),
]

PROVINCIA_CHOICES = [
    ("La Altagracia", "La Altagracia"),
]

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

    # Padres espirituales (complemento: funciona aunque NO exista el módulo Nuevo Creyente)
    padres_espirituales = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="hijos_espirituales",
        verbose_name="Padres espirituales",
    )


    telefono_norm = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        db_index=True,
        editable=False,
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
    ciudad = models.CharField(
        max_length=100,
        choices=CIUDAD_CHOICES,
        blank=True,
    )

    provincia = models.CharField(
        max_length=100,
        choices=PROVINCIA_CHOICES,
        blank=True,
    )

    codigo_postal = models.CharField(max_length=20, blank=True)
    # ------------------------------------------------------------------
    # FORMACIÓN MINISTERIAL (Pastores / Evangelistas / Misioneros, etc.)
    # ------------------------------------------------------------------

    ROL_MINISTERIAL_CHOICES = [
        ("", "—"),
        ("pastor", "Pastor"),
        ("evangelista", "Evangelista"),
        ("misionero", "Misionero"),
        ("obrero", "Obrero"),
    ]

    rol_ministerial = models.CharField(
        max_length=20,
        choices=ROL_MINISTERIAL_CHOICES,
        blank=True,
        default="",
        help_text="Rol ministerial (si aplica).",
    )

    tiene_credenciales = models.BooleanField(
        default=False,
        help_text="Indica si posee credenciales ministeriales.",
    )

    donde_estudio_teologia = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Institución / lugar donde estudió teología (si aplica).",
    )

    preparacion_teologica = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Resumen breve de la preparación teológica (si aplica).",
    )

    obrero_ordenado = models.BooleanField(
        default=False,
        help_text="Indica si es obrero ordenado.",
    )

    bautizado_espiritu_santo = models.BooleanField(
        default=False,
        help_text="Indica si está bautizado en el Espíritu Santo.",
    )

    # -------------------------
    # Datos de misión (si aplica)
    # -------------------------
    misionero_activo = models.BooleanField(
        default=False,
        help_text="Marca si actualmente está activo como misionero.",
    )

    mision_pais = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="País donde sirve como misionero (si aplica).",
    )

    mision_ciudad = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Ciudad donde sirve como misionero (si aplica).",
    )
    # -------------------------
    # Credenciales (detalle)
    # -------------------------
    numero_credencial = models.CharField(
        max_length=60,
        blank=True,
        help_text="Número o código de la credencial ministerial.",
    )

    credencial_fecha_emision = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de emisión de la credencial.",
    )

    credencial_fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento de la credencial (si aplica).",
    )

    # -------------------------
    # Estado y formación ministerial
    # -------------------------
    estado_ministerial = models.CharField(
        max_length=20,
        choices=ESTADO_MINISTERIAL_CHOICES,
        blank=True,
        default="",
        help_text="Estado actual en el ministerio.",
    )

    nivel_formacion = models.CharField(
        max_length=20,
        choices=NIVEL_FORMACION_CHOICES,
        blank=True,
        default="",
        help_text="Nivel de formación teológica.",
    )

    area_formacion = models.CharField(
        max_length=30,
        choices=AREA_FORMACION_CHOICES,
        blank=True,
        default="",
        help_text="Área principal de formación.",
    )

    cursos_certificaciones = models.TextField(
        blank=True,
        help_text="Cursos, diplomados o certificaciones relevantes.",
    )

    # -------------------------
    # Detalle de misión
    # -------------------------
    mision_tipo = models.CharField(
        max_length=20,
        choices=TIPO_MISION_CHOICES,
        blank=True,
        default="",
        help_text="Tipo de misión realizada.",
    )

    mision_fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de inicio de la misión.",
    )

    mision_fecha_fin = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de fin de la misión (si aplica).",
    )


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
        default=timezone.localdate,   # ✅ evita el prompt y rellena los NULL existentes
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
 # ======================================
    # NORMALIZAR TELÉFONO
    # ======================================
        if self.telefono:
            digits = re.sub(r"\D+", "", self.telefono)
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]
            self.telefono_norm = digits[:10] if digits else None
        else:
            self.telefono_norm = None

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

    def dias_en_iglesia(self):
        """
        Devuelve los días transcurridos entre la fecha de ingreso
        y la fecha de salida.
        Si no tiene salida, calcula hasta hoy.
        """
        if not self.fecha_ingreso_iglesia:
            return None

        fecha_fin = self.fecha_salida or date.today()
        return (fecha_fin - self.fecha_ingreso_iglesia).days
    def log_event(
            self,
            *,
            tipo,
            titulo,
            detalle="",
            user=None,
            estado_from="",
            estado_to="",
            etapa_from="",
            etapa_to="",
        ):
            from .models import MiembroBitacora  # evita imports circulares

            MiembroBitacora.objects.create(
                miembro=self,
                tipo=tipo,
                titulo=titulo,
                detalle=detalle or "",
                estado_from=estado_from or "",
                estado_to=estado_to or "",
                etapa_from=etapa_from or "",
                etapa_to=etapa_to or "",
                creado_por=user if user and getattr(user, "is_authenticated", False) else None,
                fecha=timezone.now(),
            )


    def registrar_evento(
        self,
        tipo,
        descripcion,
        detalle="",
        valor_anterior="",
        valor_nuevo="",
        usuario=None,
        referencia_tipo="",
        referencia_id=None,
    ):
        '''
        Atajo para registrar eventos en el timeline del miembro.
        
        Uso:
            miembro.registrar_evento(
                tipo="bautismo",
                descripcion="Registrado como bautizado",
                usuario=request.user,
            )
        '''
        from .models import TimelineEvent
        
        return TimelineEvent.registrar(
            miembro=self,
            tipo=tipo,
            descripcion=descripcion,
            detalle=detalle,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            usuario=usuario,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
        )
    @property
    def hogar_principal(self):
        hm = self.hogares.select_related("hogar__clan").filter(es_principal=True).first()
        return hm.hogar if hm else None

    @property
    def clan_familiar(self):
        hogar = self.hogar_principal
        return hogar.clan if hogar and hogar.clan else None

    @property
    def miembros_de_mi_hogar(self):
        hogar = self.hogar_principal
        if not hogar:
            return []
        return hogar.miembros.select_related("miembro").all()

    @property
    def hogares_de_mi_clan(self):
        clan = self.clan_familiar
        if not clan:
            return []
        return clan.hogares.prefetch_related("miembros__miembro").all()

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
            # Núcleo familiar
            "padre": ("Padre", "Padre"),
            "madre": ("Madre", "Madre"),
            "hijo": ("Hijo", "Hija"),
            "conyuge": ("Cónyuge", "Cónyuge"),
            "hermano": ("Hermano", "Hermana"),

            # Ascendientes
            "abuelo": ("Abuelo", "Abuela"),
            "bisabuelo": ("Bisabuelo", "Bisabuela"),  # ← NUEVO

            # Descendientes
            "nieto": ("Nieto", "Nieta"),
            "bisnieto": ("Bisnieto", "Bisnieta"),  # ← NUEVO

            # Colaterales
            "tio": ("Tío", "Tía"),
            "sobrino": ("Sobrino", "Sobrina"),
            "primo": ("Primo", "Prima"),

            # Políticos
            "suegro": ("Suegro", "Suegra"),
            "yerno": ("Yerno", "Nuera"),
            "cunado": ("Cuñado", "Cuñada"),
            "consuegro": ("Consuegro", "Consuegra"),  # ← NUEVO

            # Otros
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


class MiembroBitacora(models.Model):
    """
    Bitácora (historial) del miembro.
    Guarda eventos automáticos (salida, reincorporación, cambios) y notas manuales.
    """

    class Tipos(models.TextChoices):
        SISTEMA = "sistema", "Sistema"
        SALIDA = "salida", "Salida"
        REINGRESO = "reingreso", "Reincorporación"
        CAMBIO_ESTADO = "cambio_estado", "Cambio de estado"
        CAMBIO_ETAPA = "cambio_etapa", "Cambio de etapa"
        NOTA = "nota", "Nota"
        DOCUMENTO = "documento", "Documento"

    miembro = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.CASCADE,
        related_name="bitacora",
    )

    tipo = models.CharField(max_length=30, choices=Tipos.choices, default=Tipos.SISTEMA)

    titulo = models.CharField(max_length=140)
    detalle = models.TextField(blank=True, default="")

    # Campos opcionales tipo “antes / después” (muy útil)
    estado_from = models.CharField(max_length=40, blank=True, default="")
    estado_to = models.CharField(max_length=40, blank=True, default="")

    etapa_from = models.CharField(max_length=40, blank=True, default="")
    etapa_to = models.CharField(max_length=40, blank=True, default="")

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="miembro_bitacoras",
    )

    fecha = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Bitácora (Miembro)"
        verbose_name_plural = "Bitácoras (Miembro)"

    @property
    def autor(self):
        # Para que el template pueda usar item.autor como en tu chatter actual :contentReference[oaicite:2]{index=2}
        return self.creado_por

    def __str__(self):
        return f"{self.miembro_id} - {self.tipo} - {self.titulo}"



class TimelineEvent(models.Model):
    """
    Registro automático de eventos del sistema para cada miembro.
    Separado de la bitácora manual para mantener un historial limpio y automático.
    """

    class TipoEvento(models.TextChoices):
        CREACION = "creacion", "Creación"
        EDICION = "edicion", "Edición de datos"
        ESTADO = "estado", "Cambio de estado"
        ETAPA = "etapa", "Cambio de etapa"
        BAUTISMO = "bautismo", "Bautismo"
        UNIDAD_ASIGNADA = "unidad_asignada", "Asignación a unidad"
        UNIDAD_REMOVIDA = "unidad_removida", "Remoción de unidad"
        EMAIL = "email", "Envío de correo"
        BAJA = "baja", "Baja"
        REINGRESO = "reingreso", "Reingreso"
        FOTO = "foto", "Cambio de foto"
        RELACION = "relacion", "Relación familiar"
        OTRO = "otro", "Otro"

    # Iconos para cada tipo de evento (Material Icons)
    ICONOS = {
        "creacion": "person_add",
        "edicion": "edit",
        "estado": "swap_horiz",
        "etapa": "trending_up",
        "bautismo": "water_drop",
        "unidad_asignada": "group_add",
        "unidad_removida": "group_remove",
        "email": "mail",
        "baja": "person_off",
        "reingreso": "person_add_alt",
        "foto": "photo_camera",
        "relacion": "family_restroom",
        "otro": "info",
    }

    # Colores para cada tipo de evento
    COLORES = {
        "creacion": "#10b981",      # verde
        "edicion": "#6b7280",       # gris
        "estado": "#f59e0b",        # amarillo
        "etapa": "#8b5cf6",         # púrpura
        "bautismo": "#0ea5e9",      # azul cielo
        "unidad_asignada": "#0097a7", # teal
        "unidad_removida": "#ef4444", # rojo
        "email": "#3b82f6",         # azul
        "baja": "#dc2626",          # rojo oscuro
        "reingreso": "#22c55e",     # verde claro
        "foto": "#ec4899",          # rosa
        "relacion": "#a855f7",      # púrpura claro
        "otro": "#9ca3af",          # gris claro
    }

    miembro = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.CASCADE,
        related_name="timeline",
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoEvento.choices,
        default=TipoEvento.OTRO,
        db_index=True,
    )

    descripcion = models.CharField(
        max_length=255,
        help_text="Descripción corta del evento",
    )

    detalle = models.TextField(
        blank=True,
        default="",
        help_text="Información adicional del evento (opcional)",
    )

    # Valores para cambios (de → a)
    valor_anterior = models.CharField(max_length=100, blank=True, default="")
    valor_nuevo = models.CharField(max_length=100, blank=True, default="")

    # Metadatos
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_events",
    )

    fecha = models.DateTimeField(default=timezone.now, db_index=True)

    # Campo para referencias (ej: ID de unidad, ID de email, etc.)
    referencia_tipo = models.CharField(max_length=50, blank=True, default="")
    referencia_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Evento de Timeline"
        verbose_name_plural = "Eventos de Timeline"
        indexes = [
            models.Index(fields=["miembro", "-fecha"]),
            models.Index(fields=["tipo", "-fecha"]),
        ]

    def __str__(self):
        return f"{self.miembro} - {self.get_tipo_display()} - {self.fecha:%d/%m/%Y}"

    @property
    def icono(self):
        return self.ICONOS.get(self.tipo, "info")

    @property
    def color(self):
        return self.COLORES.get(self.tipo, "#9ca3af")


    # ═══════════════════════════════════════════════════════════════════════════
    # HELPER PARA REGISTRAR EVENTOS FÁCILMENTE
    # ═══════════════════════════════════════════════════════════════════════════
    @classmethod
    def registrar(
        cls,
        miembro,
        tipo,
        descripcion,
        detalle="",
        valor_anterior="",
        valor_nuevo="",
        usuario=None,
        referencia_tipo="",
        referencia_id=None,
    ):
        """
        Helper para registrar eventos de forma sencilla.
        
        Ejemplo de uso:
            TimelineEvent.registrar(
                miembro=miembro,
                tipo="estado",
                descripcion="Cambio de estado",
                valor_anterior="Activo",
                valor_nuevo="Pasivo",
                usuario=request.user,
            )
        """
        return cls.objects.create(
            miembro=miembro,
            tipo=tipo,
            descripcion=descripcion,
            detalle=detalle,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            usuario=usuario if usuario and getattr(usuario, "is_authenticated", False) else None,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
        )

class ZonaGeo(models.Model):
    """
    Guarda coordenadas (lat/lng) por zona para no geocodificar cada vez.
    Zona = combinación sector + ciudad + provincia.
    """
    sector = models.CharField(max_length=100, blank=True, default="")

    ciudad = models.CharField(
        max_length=50,
        choices=CIUDAD_CHOICES,
        blank=True,
        default="Higuey",
    )

    provincia = models.CharField(
        max_length=50,
        choices=PROVINCIA_CHOICES,
        blank=True,
        default="La Altagracia",
    )

    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("sector", "ciudad", "provincia")
        ordering = ["provincia", "ciudad", "sector"]
        verbose_name = "Zona (Geo)"
        verbose_name_plural = "Zonas (Geo)"

    def __str__(self):
        parts = [p for p in [self.sector, self.ciudad, self.provincia] if p]
        return " / ".join(parts) if parts else "—"

# ==========================================================
# ✅ FAMILIAS INTELIGENTES (HOGAR + CLAN)
# ==========================================================

class ClanFamiliar(models.Model):
    """
    Familia extendida (padres + hijos + nietos...). Aquí caen varios hogares.
    Ej: "Familia Pérez" (incluye el hogar de Jonathan y el hogar del hermano).
    """
    nombre = models.CharField(max_length=150)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class HogarFamiliar(models.Model):
    """
    Familia nuclear (hogar): pareja + hijos.
    Cada pareja normalmente crea un hogar.
    """
    clan = models.ForeignKey(
        ClanFamiliar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hogares"
    )
    nombre = models.CharField(max_length=150, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre or f"Hogar #{self.pk}"


class HogarMiembro(models.Model):
    """
    Miembros dentro de un hogar (roles: padre, madre, hijo).
    """
    ROL_CHOICES = [
        ("padre", "Padre"),
        ("madre", "Madre"),
        ("hijo", "Hijo/Hija"),
        ("otro", "Otro"),
    ]

    hogar = models.ForeignKey(HogarFamiliar, on_delete=models.CASCADE, related_name="miembros")
    miembro = models.ForeignKey("Miembro", on_delete=models.CASCADE, related_name="hogares")
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    es_principal = models.BooleanField(default=False)

    class Meta:
        unique_together = ("hogar", "miembro")

    def __str__(self):
        return f"{self.miembro} → {self.hogar} ({self.rol})"


# ==========================================================
# ✅ HELPERS (LÓGICA “INTELIGENTE”)
# ==========================================================

def _norm_genero(g):
    g = (g or "").strip().lower()
    if g in ("m", "masculino", "hombre"):
        return "m"
    if g in ("f", "femenino", "mujer"):
        return "f"
    return ""


def _rol_padre_o_madre_por_genero(miembro):
    gen = _norm_genero(getattr(miembro, "genero", ""))
    return "madre" if gen == "f" else "padre"


def _buscar_clan_desde_padres(miembro):
    """
    Si el miembro tiene padre/madre definidos en MiembroRelacion,
    buscamos el hogar principal de ese padre/madre y usamos su clan.
    Así dos hermanos comparten clan automáticamente.
    """
    padres = (
        MiembroRelacion.objects
        .filter(miembro=miembro, tipo_relacion__in=["padre", "madre"])
        .select_related("familiar")
    )

    for rel in padres:
        padre_madre = rel.familiar
        hm = (
            HogarMiembro.objects
            .filter(miembro=padre_madre, es_principal=True)
            .select_related("hogar__clan")
            .first()
        )
        if hm and hm.hogar and hm.hogar.clan:
            return hm.hogar.clan

    return None


@transaction.atomic
def asegurar_hogar_para_miembro(miembro, clan_sugerido=None):
    """
    Si el miembro no tiene hogar principal, crea uno (hogar unipersonal por ahora).
    """
    existente = HogarMiembro.objects.filter(miembro=miembro, es_principal=True).select_related("hogar").first()
    if existente:
        return existente.hogar

    clan = clan_sugerido or _buscar_clan_desde_padres(miembro)
    if clan is None:
        clan = ClanFamiliar.objects.create(nombre=f"Clan de {miembro.apellidos}".strip() if getattr(miembro, "apellidos", "") else f"Clan #{miembro.pk}")

    hogar = HogarFamiliar.objects.create(
        clan=clan,
        nombre=f"Hogar de {miembro.nombres} {miembro.apellidos}".strip()
    )

    HogarMiembro.objects.create(
        hogar=hogar,
        miembro=miembro,
        rol=_rol_padre_o_madre_por_genero(miembro),
        es_principal=True
    )

    return hogar


@transaction.atomic
def sync_familia_inteligente_por_relacion(relacion: "MiembroRelacion"):
    """
    Se llama cuando se crea una relación.
    Reglas:
    - Si se crea CÓNYUGE: crea/asegura hogar para la pareja y los une en el mismo hogar.
    - Si se crea HIJO: mete al hijo en el hogar del padre/madre.
    - Si se crea PADRE/MADRE: mete al miembro como hijo en el hogar del padre/madre.
    """
    miembro = relacion.miembro
    familiar = relacion.familiar
    tipo = relacion.tipo_relacion

    # 1) Cónyuge: mismo hogar (familia nuclear)
    if tipo == "conyuge":
        # Intentamos heredar clan desde los padres de cualquiera de los dos
        clan = _buscar_clan_desde_padres(miembro) or _buscar_clan_desde_padres(familiar)

        hogar_miembro = asegurar_hogar_para_miembro(miembro, clan_sugerido=clan)

        # Asegurar que el cónyuge esté en el mismo hogar
        HogarMiembro.objects.get_or_create(
            hogar=hogar_miembro,
            miembro=familiar,
            defaults={"rol": _rol_padre_o_madre_por_genero(familiar), "es_principal": True}
        )

        # Marcar ambos como principales (opcional, pero útil)
        HogarMiembro.objects.filter(hogar=hogar_miembro, miembro__in=[miembro, familiar]).update(es_principal=True)

        # Nombre bonito del hogar (opcional)
        if not hogar_miembro.nombre:
            hogar_miembro.nombre = f"Hogar de {miembro.apellidos}".strip() if getattr(miembro, "apellidos", "") else f"Hogar #{hogar_miembro.pk}"
            hogar_miembro.save(update_fields=["nombre"])

        return

    # 2) Hijo: hijo dentro del hogar del padre/madre
    if tipo == "hijo":
        hogar = asegurar_hogar_para_miembro(miembro)
        HogarMiembro.objects.get_or_create(
            hogar=hogar,
            miembro=familiar,
            defaults={"rol": "hijo", "es_principal": False}
        )
        return

    # 3) Padre/Madre: el miembro es hijo del padre/madre
    if tipo in ("padre", "madre"):
        hogar_padre = asegurar_hogar_para_miembro(familiar)  # familiar es el padre/madre
        HogarMiembro.objects.get_or_create(
            hogar=hogar_padre,
            miembro=miembro,
            defaults={"rol": "hijo", "es_principal": False}
        )
        return
