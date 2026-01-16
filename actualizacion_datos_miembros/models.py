from django.db import models
from django.utils import timezone
import uuid

from miembros_app.models import Miembro, GENERO_CHOICES, ESTADO_MIEMBRO_CHOICES


class AccesoActualizacionDatos(models.Model):
    """
    Link único (sin login) por Miembro.
    - Se genera 1 vez y se reutiliza siempre.
    """
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
    # Después de los campos de contacto existentes:
    telefono_secundario = models.CharField(max_length=20, blank=True)

    # Datos personales:
    lugar_nacimiento = models.CharField(max_length=150, blank=True)
    nacionalidad = models.CharField(max_length=100, blank=True)
    estado_civil = models.CharField(max_length=20, blank=True)
    nivel_educativo = models.CharField(max_length=50, blank=True)
    profesion = models.CharField(max_length=100, blank=True)
    pasaporte = models.CharField(max_length=30, blank=True)

    # Membresía (estos ya los tienes, verifica):
    iglesia_anterior = models.CharField(max_length=150, blank=True)
    fecha_conversion = models.DateField(blank=True, null=True)
    fecha_bautismo = models.DateField(blank=True, null=True)
    fecha_ingreso_iglesia = models.DateField(blank=True, null=True)

    # --- Datos editables (seguros) ---
    telefono = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    direccion = models.TextField(blank=True)
    sector = models.CharField(max_length=100, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    provincia = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=20, blank=True)

        # --- Membresía (para actualizar por etapas) ---
    iglesia_anterior = models.CharField(max_length=150, blank=True)

    fecha_conversion = models.DateField(blank=True, null=True)
    fecha_bautismo = models.DateField(blank=True, null=True)
    fecha_ingreso_iglesia = models.DateField(blank=True, null=True)



    empleador = models.CharField(max_length=150, blank=True)
    puesto = models.CharField(max_length=100, blank=True)
    telefono_trabajo = models.CharField(max_length=20, blank=True)
    direccion_trabajo = models.TextField(blank=True)

    contacto_emergencia_nombre = models.CharField(max_length=150, blank=True)
    contacto_emergencia_telefono = models.CharField(max_length=20, blank=True)
    contacto_emergencia_relacion = models.CharField(max_length=50, blank=True)

    # Salud (opcional)
    tipo_sangre = models.CharField(max_length=10, blank=True)
    alergias = models.TextField(blank=True)
    condiciones_medicas = models.TextField(blank=True)
    medicamentos = models.TextField(blank=True)

    # Auditoría
    creado_en = models.DateTimeField(default=timezone.now)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

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

    estado = models.CharField(
        max_length=20,
        choices=Estados.choices,
        default=Estados.PENDIENTE,
    )

        # Documentos opcionales
    foto = models.ImageField(upload_to="solicitudes_alta/fotos/", blank=True, null=True)
    cedula = models.CharField(max_length=20, blank=True)


    # Datos mínimos de alta masiva
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)

    genero = models.CharField(max_length=20, choices=GENERO_CHOICES)
    fecha_nacimiento = models.DateField()

    estado_miembro = models.CharField(max_length=30, choices=ESTADO_MIEMBRO_CHOICES)
    
    telefono = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    sector = models.CharField(max_length=100, blank=True)

    # Auditoría
    creado_en = models.DateTimeField(default=timezone.now)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

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

from django.db import models

class AltaMasivaConfig(models.Model):
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

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
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
        return "Alta masiva: " + ("Activa" if self.activo else "Cerrada")



class ActualizacionDatosConfig(models.Model):
    """
    Configuración GLOBAL: define qué campos se muestran en el formulario público
    de actualización para TODOS los miembros.
    """
    activo = models.BooleanField(default=True)

    # Lista de nombres de campos permitidos (strings), ej:
    # ["telefono", "whatsapp", "email", "direccion"]
    campos_permitidos = models.JSONField(default=list, blank=True)

    actualizado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Configuración de Actualización de Datos"
        verbose_name_plural = "Configuración de Actualización de Datos"

    def __str__(self):
        return "Configuración global de actualización"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"activo": True, "campos_permitidos": []})
        return obj