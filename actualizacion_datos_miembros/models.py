from django.db import models
from django.utils import timezone
import uuid

from miembros_app.models import Miembro, GENERO_CHOICES, ESTADO_MIEMBRO_CHOICES, CIUDAD_CHOICES
from tenants.models import Tenant


class AccesoActualizacionDatos(models.Model):
    """
    Link único (sin login) por Miembro.
    """
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='accesos_actualizacion_datos'
    )
    miembro = models.OneToOneField(
        Miembro,
        on_delete=models.CASCADE,
        related_name="acceso_actualizacion_datos",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(auto_now=True)
    ultimo_envio_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Acceso: actualización de datos"
        verbose_name_plural = "Accesos: actualización de datos"

    def __str__(self):
        return f"Acceso({self.miembro_id}) activo={self.activo}"


class SolicitudActualizacionMiembro(models.Model):
    class Estados(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APLICADA = "aplicada", "Aplicada"
        RECHAZADA = "rechazada", "Rechazada"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='solicitudes_actualizacion_miembro'
    )
    miembro = models.ForeignKey(
        Miembro,
        on_delete=models.CASCADE,
        related_name="solicitudes_actualizacion",
    )

    estado = models.CharField(
        max_length=20,
        choices=Estados.choices,
        default=Estados.PENDIENTE,
    )

    # Contacto
    telefono = models.CharField(max_length=20, blank=True)
    telefono_secundario = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # Dirección
    direccion = models.TextField(blank=True)
    sector = models.CharField(max_length=100, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    provincia = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=20, blank=True)

    # Datos personales
    lugar_nacimiento = models.CharField(max_length=150, blank=True)
    nacionalidad = models.CharField(max_length=100, blank=True)
    estado_civil = models.CharField(max_length=20, blank=True)
    nivel_educativo = models.CharField(max_length=50, blank=True)
    profesion = models.CharField(max_length=100, blank=True)
    pasaporte = models.CharField(max_length=30, blank=True)

    # Membresía
    iglesia_anterior = models.CharField(max_length=150, blank=True)
    fecha_conversion = models.DateField(blank=True, null=True)
    fecha_bautismo = models.DateField(blank=True, null=True)
    fecha_ingreso_iglesia = models.DateField(blank=True, null=True)

    # Trabajo
    empleador = models.CharField(max_length=150, blank=True)
    puesto = models.CharField(max_length=100, blank=True)
    telefono_trabajo = models.CharField(max_length=20, blank=True)
    direccion_trabajo = models.TextField(blank=True)

    # Contacto emergencia
    contacto_emergencia_nombre = models.CharField(max_length=150, blank=True)
    contacto_emergencia_telefono = models.CharField(max_length=20, blank=True)
    contacto_emergencia_relacion = models.CharField(max_length=50, blank=True)

    # Salud
    tipo_sangre = models.CharField(max_length=10, blank=True)
    alergias = models.TextField(blank=True)
    condiciones_medicas = models.TextField(blank=True)
    medicamentos = models.TextField(blank=True)

    # Auditoría creación
    creado_en = models.DateTimeField(default=timezone.now)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    # Auditoría revisión
    revisado_en = models.DateTimeField(null=True, blank=True)
    revisado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_actualizacion_revisadas",
    )
    nota_admin = models.TextField(blank=True)

    class Meta:
        verbose_name = "Solicitud: actualización de datos"
        verbose_name_plural = "Solicitudes: actualización de datos"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Solicitud({self.pk}) {self.miembro_id} {self.estado}"


class SolicitudAltaMiembro(models.Model):
    class Estados(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='solicitudes_alta_miembro'
    )
    estado = models.CharField(
        max_length=20,
        choices=Estados.choices,
        default=Estados.PENDIENTE,
    )

    # Documentos
    foto = models.ImageField(upload_to="solicitudes_alta/fotos/", blank=True, null=True)
    cedula = models.CharField(max_length=20, blank=True)

    # Datos básicos
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    apodo = models.CharField(max_length=50, blank=True) 
    genero = models.CharField(max_length=20, choices=GENERO_CHOICES)
    fecha_nacimiento = models.DateField()
    estado_miembro = models.CharField(max_length=30, choices=ESTADO_MIEMBRO_CHOICES)

    # Contacto
    telefono = models.CharField(max_length=20, blank=True)  # Ya no obligatorio
    whatsapp = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    sector = models.CharField(max_length=100)  # Obligatorio
    ciudad = models.CharField(
        max_length=50,
        choices=CIUDAD_CHOICES,
        default="Higuey",
    )

    # Membresía
    fecha_ingreso_iglesia = models.DateField()

    # Auditoría creación
    creado_en = models.DateTimeField(default=timezone.now)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    # Auditoría revisión
    revisado_en = models.DateTimeField(null=True, blank=True)
    revisado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_alta_revisadas",
    )
    nota_admin = models.TextField(blank=True)

    class Meta:
        verbose_name = "Solicitud: alta (registro masivo)"
        verbose_name_plural = "Solicitudes: altas (registro masivo)"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Alta({self.pk}) {self.nombres} {self.apellidos} - {self.estado}"


class AltaMasivaConfig(models.Model):
    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE,
        related_name='alta_masiva_config'
    )
    activo = models.BooleanField(default=True)
    mensaje_compartir = models.TextField(
        default=(
            "Registro de miembro\n\n"
            "Hola 👋\n"
            "Estamos probando un formulario digital para registrar datos de la iglesia.\n"
            "¿Podrías llenarlo y decirme si algo no se entiende?\n\n"
            "Gracias 🙏"
        )
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración: alta masiva"
        verbose_name_plural = "Configuración: alta masiva"

    @classmethod
    def get_solo(cls, tenant):
        obj, _ = cls.objects.get_or_create(
            tenant=tenant,
            defaults={
                "activo": True,
                "mensaje_compartir": (
                    "Registro de miembro\n\n"
                    "Hola 👋\n"
                    "Estamos probando un formulario digital para registrar datos de la iglesia.\n"
                    "¿Podrías llenarlo y decirme si algo no se entiende?\n\n"
                    "Gracias 🙏"
                ),
            },
        )
        return obj

    def __str__(self):
        return f"Alta masiva: " + ("Activa" if self.activo else "Cerrada")


class ActualizacionDatosConfig(models.Model):
    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE,
        related_name='actualizacion_datos_config'
    )
    activo = models.BooleanField(default=True)
    campos_permitidos = models.JSONField(default=list, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración: actualización de datos"
        verbose_name_plural = "Configuración: actualización de datos"

    @classmethod
    def get_solo(cls, tenant):
        obj, _ = cls.objects.get_or_create(
            tenant=tenant,
            defaults={"activo": True, "campos_permitidos": []}
        )
        return obj

    def __str__(self):
        return f"Config actualización datos"


class AccesoAltaFamilia(models.Model):
    """Link público para alta de familia."""
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='accesos_alta_familia'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(auto_now=True)
    ultimo_envio_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Acceso: alta de familia"
        verbose_name_plural = "Accesos: alta de familia"

    def __str__(self):
        return f"AccesoAltaFamilia(token={self.token}) activo={self.activo}"


class AltaFamiliaLog(models.Model):
    """Solicitud de alta de familia."""
    class Estados(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APLICADA = "aplicada", "Aplicada"
        RECHAZADA = "rechazada", "Rechazada"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='altas_familia_logs'
    )
    acceso = models.ForeignKey(
        AccesoAltaFamilia,
        on_delete=models.CASCADE,
        related_name="logs",
        null=True,
        blank=True,
    )
    principal = models.ForeignKey(
        Miembro,
        on_delete=models.CASCADE,
        related_name="altas_familia_como_principal",
        null=True,
        blank=True,
    )
    estado = models.CharField(
        max_length=20,
        choices=Estados.choices,
        default=Estados.PENDIENTE,
    )

    creado_en = models.DateTimeField(default=timezone.now)

    # IDs enviados
    conyuge_id = models.IntegerField(null=True, blank=True)
    padre_id = models.IntegerField(null=True, blank=True)
    madre_id = models.IntegerField(null=True, blank=True)
    hijos_ids = models.JSONField(default=list, blank=True)

    # Resultado
    relaciones_creadas = models.JSONField(default=list, blank=True)
    alertas = models.JSONField(default=list, blank=True)

    # Auditoría revisión
    revisado_en = models.DateTimeField(null=True, blank=True)
    revisado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_familia_revisadas",
    )
    nota_admin = models.TextField(blank=True)

    # Auditoría origen
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Solicitud: alta de familia"
        verbose_name_plural = "Solicitudes: alta de familia"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"AltaFamilia({self.pk}) principal={self.principal_id} - {self.estado}"

    def get_conyuge(self):
        if self.conyuge_id:
            return Miembro.objects.filter(pk=self.conyuge_id).first()
        return None

    def get_padre(self):
        if self.padre_id:
            return Miembro.objects.filter(pk=self.padre_id).first()
        return None

    def get_madre(self):
        if self.madre_id:
            return Miembro.objects.filter(pk=self.madre_id).first()
        return None

    def get_hijos(self):
        if self.hijos_ids:
            return Miembro.objects.filter(pk__in=self.hijos_ids)
        return Miembro.objects.none()