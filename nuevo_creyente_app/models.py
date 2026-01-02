from django.conf import settings
from django.db import models
from django.utils import timezone

from miembros_app.models import Miembro


class NuevoCreyenteExpediente(models.Model):
    class Estados(models.TextChoices):
        EN_SEGUIMIENTO = "EN_SEGUIMIENTO", "En seguimiento"
        CERRADO = "CERRADO", "Cerrado"

    class Etapas(models.TextChoices):
        INICIO = "INICIO", "Inicio"
        PRIMER_CONTACTO = "PRIMER_CONTACTO", "Primer contacto"
        ACOMPANAMIENTO = "ACOMPANAMIENTO", "Acompañamiento"
        INTEGRACION = "INTEGRACION", "Integración"
        EVALUACION = "EVALUACION", "Evaluación"
        CIERRE = "CIERRE", "Cierre"

    ETAPAS_ORDEN = [
        Etapas.INICIO,
        Etapas.PRIMER_CONTACTO,
        Etapas.ACOMPANAMIENTO,
        Etapas.INTEGRACION,
        Etapas.EVALUACION,
        Etapas.CIERRE,
    ]

    miembro = models.OneToOneField(
        Miembro,
        on_delete=models.CASCADE,
        related_name="expediente_nuevo_creyente",
        help_text="Miembro enviado al módulo de Nuevo Creyente.",
    )

    unidad_responsable = models.ForeignKey(
        "estructura_app.Unidad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_nuevo_creyente",
        help_text="Unidad responsable del seguimiento del nuevo creyente.",
    )

    estado = models.CharField(
        max_length=20,
        choices=Estados.choices,
        default=Estados.EN_SEGUIMIENTO,
        db_index=True,
    )

    etapa = models.CharField(
        max_length=30,
        choices=Etapas.choices,
        default=Etapas.INICIO,
        db_index=True,
        help_text="Etapa actual del ciclo de seguimiento (manual asistido).",
    )

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_nuevo_creyente",
    )

    padres_espirituales = models.ManyToManyField(
        "miembros_app.Miembro",
        through="NuevoCreyentePadreEspiritual",
        blank=True,
        related_name="expedientes_nuevo_creyente_padrinos",
    )

    fecha_envio = models.DateTimeField(default=timezone.now, db_index=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    proximo_contacto = models.DateField(null=True, blank=True)

    notas = models.TextField(blank=True, default="")

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    from django.utils import timezone

    def log_event(
        self,
        *,
        tipo,
        titulo,
        detalle="",
        user=None,
        canal="",
        resultado_contacto="",
        etapa_from="",
        etapa_to="",
        padre_miembro_id=None,
        padre_nombre="",
        padre_accion="",
    ):
        """
        Crea una entrada en la bitácora del expediente.
        """
        from .models import NuevoCreyenteBitacora  # evita imports circulares

        NuevoCreyenteBitacora.objects.create(
            expediente=self,
            tipo=tipo,
            titulo=titulo,
            detalle=detalle or "",
            canal=canal or "",
            resultado_contacto=resultado_contacto or "",
            etapa_from=etapa_from or "",
            etapa_to=etapa_to or "",
            padre_miembro_id=padre_miembro_id,
            padre_nombre=padre_nombre or "",
            padre_accion=padre_accion or "",
            creado_por=user if user and getattr(user, "is_authenticated", False) else None,
            fecha=timezone.now(),
        )


    def log_inicio(self, user=None):
        self.log_event(
            tipo="sistema",
            titulo="Seguimiento iniciado",
            detalle="Enviado al módulo de Nuevo Creyente.",
            user=user,
        )


    def log_cambio_etapa(self, *, etapa_from, etapa_to, user=None):
        self.log_event(
            tipo="etapa",
            titulo="Cambio de etapa",
            detalle=f"De: {etapa_from} → {etapa_to}",
            etapa_from=etapa_from,
            etapa_to=etapa_to,
            user=user,
        )


    def log_padre(self, *, accion, padre_miembro_id=None, padre_nombre="", user=None):
        # accion: "add" | "remove"
        titulo = "Padre espiritual asignado" if accion == "add" else "Padre espiritual retirado"
        self.log_event(
            tipo="padre",
            titulo=titulo,
            detalle=padre_nombre,
            padre_miembro_id=padre_miembro_id,
            padre_nombre=padre_nombre,
            padre_accion=accion,
            user=user,
        )


    def log_cierre(self, user=None):
        self.log_event(
            tipo="cierre",
            titulo="Seguimiento cerrado",
            detalle="El expediente fue cerrado.",
            user=user,
        )


    def log_nota(self, *, texto, user=None):
        self.log_event(
            tipo="nota",
            titulo="Nota",
            detalle=texto,
            user=user,
        )


    class Meta:
        verbose_name = "Expediente (Nuevo Creyente)"
        verbose_name_plural = "Expedientes (Nuevo Creyente)"
        ordering = ["-fecha_envio", "-fecha_creacion"]

    def __str__(self):
        return f"NC - {self.miembro} ({self.get_estado_display()})"

    def etapa_index(self):
        try:
            return self.ETAPAS_ORDEN.index(self.etapa)
        except ValueError:
            return 0

    def etapa_sugerencia(self):
        return {
            self.Etapas.INICIO: "Asigna responsable y define el próximo contacto.",
            self.Etapas.PRIMER_CONTACTO: "Recomendado: llamada o mensaje en 3–5 días.",
            self.Etapas.ACOMPANAMIENTO: "Acompaña con un segundo contacto y escucha activa.",
            self.Etapas.INTEGRACION: "Invita a célula / grupo pequeño o actividad sencilla.",
            self.Etapas.EVALUACION: "Evalúa barreras y define el siguiente paso (discipulado, célula, etc.).",
            self.Etapas.CIERRE: "Seguimiento completado. Ya no requiere cuidado intensivo.",
        }.get(self.etapa, "")

    def puede_cerrar(self):
        return self.estado == self.Estados.EN_SEGUIMIENTO and self.etapa == self.Etapas.EVALUACION

    def cerrar(self, user=None):
        self.estado = self.Estados.CERRADO
        self.etapa = self.Etapas.CIERRE
        self.fecha_cierre = timezone.now()
        self.save(update_fields=["estado", "etapa", "fecha_cierre", "fecha_actualizacion"])


class NuevoCreyentePadreEspiritual(models.Model):
    expediente = models.ForeignKey(
        "NuevoCreyenteExpediente",
        on_delete=models.CASCADE,
        related_name="padres_links",
    )
    padre = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.CASCADE,
        related_name="nuevo_creyente_padrino_links",
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("expediente", "padre")

    def __str__(self):
        return f"{self.expediente_id} -> {self.padre_id}"


class NuevoCreyenteBitacora(models.Model):
    """
    Bitácora (historial) de un expediente de Nuevo Creyente.
    Guarda eventos automáticos (etapa, cierre, padres espirituales) y notas manuales.
    """

    class Tipos(models.TextChoices):
        SISTEMA = "sistema", "Sistema"
        CONTACTO = "contacto", "Contacto"
        ACOMPANAMIENTO = "acompanamiento", "Acompañamiento"  # ✅ NUEVO
        EVALUACION = "evaluacion", "Evaluación"
        INTEGRACION = "integracion", "Integración" 
        ETAPA = "etapa", "Cambio de etapa"
        PADRE = "padre", "Padre espiritual"
        NOTA = "nota", "Nota"
        CIERRE = "cierre", "Cierre"


    class Canales(models.TextChoices):
        LLAMADA = "llamada", "Llamada"
        WHATSAPP = "whatsapp", "WhatsApp"
        PRESENCIAL = "presencial", "Presencial"
        REFERIDO = "referido", "Familiar / Referido"
        OTRO = "otro", "Otro"

    class ResultadosContacto(models.TextChoices):
        CONTACTADO = "contactado", "Contactado"
        NO_RESPONDE = "no_responde", "No respondió"
        NUM_ERR = "num_err", "Número incorrecto"
        PENDIENTE = "pendiente", "Pendiente (acordado luego)"

    expediente = models.ForeignKey(
        "nuevo_creyente_app.NuevoCreyenteExpediente",
        on_delete=models.CASCADE,
        related_name="bitacora",
    )

    tipo = models.CharField(max_length=20, choices=Tipos.choices, default=Tipos.SISTEMA)

    # Texto principal visible
    titulo = models.CharField(max_length=120)
    detalle = models.TextField(blank=True, default="")

    # Datos opcionales para eventos específicos (sin crear mil tablas)
    canal = models.CharField(max_length=20, choices=Canales.choices, blank=True, default="")
    resultado_contacto = models.CharField(
        max_length=20, choices=ResultadosContacto.choices, blank=True, default=""
    )

    etapa_from = models.CharField(max_length=30, blank=True, default="")
    etapa_to = models.CharField(max_length=30, blank=True, default="")

    # Para registrar padres espirituales sin acoplar a Miembro (guardamos ids y nombres)
    padre_miembro_id = models.IntegerField(null=True, blank=True)
    padre_nombre = models.CharField(max_length=120, blank=True, default="")
    padre_accion = models.CharField(max_length=20, blank=True, default="")  # "add" / "remove"

    # Auditoría
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="nc_bitacoras",
    )
    fecha = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Bitácora Nuevo Creyente"
        verbose_name_plural = "Bitácoras Nuevo Creyente"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"