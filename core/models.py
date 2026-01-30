from django.db import models
from cloudinary_storage.storage import RawMediaCloudinaryStorage

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
        help_text="Ej: groups, dashboard, settings (Material Icons)"
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
        help_text="El name de la ruta en urls.py, ej: core:configuracion"
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

    # IDENTIDAD INSTITUCIONAL
    nombre_iglesia = models.CharField(
        "Nombre de la iglesia",
        max_length=150,
        default="Iglesia Torre Fuerte",
    )
    nombre_corto = models.CharField(
        "Nombre corto",
        max_length=100,
        blank=True,
        help_text="Ej: Torre Fuerte, TF, etc."
    )
    denominacion = models.CharField(
        "Denominación",
        max_length=100,
        blank=True,
        help_text="Ej: Pentecostal, Bautista, Independiente, etc."
    )
    lema = models.CharField(
        "Lema / frase institucional",
        max_length=150,
        blank=True,
        help_text="Ej: 'Firmes en la Roca', 'Un refugio en la tormenta', etc."
    )
    direccion = models.TextField(
        "Dirección",
        blank=True
    )
    pastor_principal = models.CharField(
        "Pastor principal",
        max_length=150,
        blank=True,
        help_text="Nombre que se mostrará en cartas y documentos oficiales."
    )
    email_pastor = models.EmailField(
        "Correo del pastor / administración",
        blank=True,
        help_text="Correo para recibir notificaciones o copias de reportes."
    )

    # MARCA Y LOGOS
    logo = models.ImageField(
        "Logo principal (fondo claro)",
        upload_to="configuracion/",
        blank=True,
        null=True
    )
    logo_oscuro = models.ImageField(
        "Logo para fondo oscuro",
        upload_to="configuracion/",
        blank=True,
        null=True
    )
    plantilla_pdf_fondo = models.ImageField(
        "Fondo para PDFs / cartas",
        upload_to="configuracion/",
        blank=True,
        null=True,
        help_text="Imagen suave para utilizar como fondo o marca de agua en documentos."
    )
        # CONTACTO Y COMUNICACIÓN
    email_oficial = models.EmailField(
        "Correo oficial",
        blank=True
    )
    telefono_oficial = models.CharField(
        "Teléfono oficial",
        max_length=50,
        blank=True
    )
    whatsapp_oficial = models.CharField(
        "WhatsApp oficial",
        max_length=50,
        blank=True,
        help_text="Solo números con código de país, sin espacios ni guiones."
    )

    encargado_comunicaciones = models.CharField(
        "Nombre del encargado de comunicaciones",
        max_length=150,
        blank=True,
        help_text="Ej: Secretaría, Administración, Ministerio de Comunicaciones."
    )

    horario_atencion = models.CharField(
        "Horario de atención",
        max_length=150,
        blank=True,
        help_text="Ej: Lun–Vie 9:00 a.m. – 6:00 p.m."
    )

    sitio_web = models.URLField(
        "Página web oficial",
        blank=True
    )

    facebook_url = models.URLField(
        "Facebook",
        blank=True
    )

    instagram_url = models.URLField(
        "Instagram",
        blank=True
    )

    mensaje_institucional_corto = models.CharField(
        "Mensaje institucional corto",
        max_length=150,
        blank=True,
        help_text="Se puede usar como firma en correos y reportes."
    )


    # FORMATO Y ESTILO
    zona_horaria = models.CharField(
        "Zona horaria",
        max_length=50,
        default="America/Santo_Domingo",
        help_text="Ej: America/Santo_Domingo"
    )
    formato_fecha_corta = models.CharField(
        "Formato fecha corta",
        max_length=20,
        default="DD/MM/YYYY",
        help_text="Ej: DD/MM/YYYY"
    )
    formato_fecha_larga = models.CharField(
        "Formato fecha larga",
        max_length=50,
        default="D de MMMM de YYYY",
        help_text="Ej: 25 de noviembre de 2025"
    )
    color_primario = models.CharField(
        "Color primario del sistema",
        max_length=20,
        default="#0097A7",
        help_text="Color principal de la interfaz (hex)."
    )
    color_secundario = models.CharField(
        "Color secundario del sistema",
        max_length=20,
        default="#F59E0B",
        help_text="Color de acento (hex)."
    )
    MODO_IMPRESION_CHOICES = [
        ("formal", "Formal"),
        ("minimalista", "Minimalista"),
        ("clasico", "Clásico"),
    ]
    modo_impresion = models.CharField(
        "Modo de impresión",
        max_length=20,
        choices=MODO_IMPRESION_CHOICES,
        default="formal",
        help_text="Afecta el estilo de cartas, certificados y reportes."
    )
    mostrar_logo_en_reportes = models.BooleanField(
        "Mostrar logo en reportes",
        default=True,
        help_text="Si está marcado, el logo aparecerá en los reportes impresos."
    )
    mostrar_direccion_en_reportes = models.BooleanField(
        "Mostrar dirección en reportes",
        default=True,
        help_text="Si está marcado, la dirección aparecerá bajo el logo en los reportes."
    )

    # PARÁMETROS DE MEMBRESÍA Y REPORTES
    edad_minima_miembro_oficial = models.PositiveIntegerField(
        "Edad mínima miembro oficial",
        default=12,
        help_text="Años para considerar a alguien miembro oficial / bautizable."
    )
    pie_cartas = models.TextField(
        "Texto de pie de cartas",
        blank=True,
        help_text="Se puede mostrar al final de las cartas de salida, traslados, etc."
    )

    # CORREO Y NOTIFICACIONES
    email_from_name = models.CharField(
        "Nombre remitente de correos",
        max_length=100,
        blank=True,
        help_text="Ej: Iglesia Torre Fuerte."
    )
    email_from_address = models.EmailField(
        "Correo remitente de correos",
        blank=True,
        help_text="Dirección desde la que el sistema enviará correos."
    )
    enviar_copia_a_pastor = models.BooleanField(
        "Enviar copia al pastor",
        default=False,
        help_text="Si está marcado, el sistema enviará copia al correo del pastor en los correos oficiales."
    )
    codigo_miembro_prefijo = models.CharField(
        "Prefijo para código de miembro",
        max_length=20,
        default="TF-",
        help_text="Ej: TF-, IB-, CC-, etc."
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

class UserLoginHistory(models.Model):
    """Rastrea el historial de logins para mensajes de bienvenida."""
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='login_history'
    )
    login_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    
    class Meta:
        verbose_name = "Historial de Login"
        verbose_name_plural = "Historial de Logins"
        ordering = ['-login_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_at.strftime('%d/%m/%Y %H:%M')}"
    
    @classmethod
    def register_login(cls, user, request=None):
        previous = cls.objects.filter(user=user).order_by('-login_at').first()
        
        ip = None
        user_agent = ''
        if request:
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        cls.objects.create(user=user, ip_address=ip, user_agent=user_agent)
        
        old = list(cls.objects.filter(user=user).order_by('-login_at').values_list('pk', flat=True)[10:])
        if old:
            cls.objects.filter(pk__in=old).delete()
        
        return previous
    
class UserEngagement(models.Model):
    """Trackea engagement del usuario para mensajes inteligentes."""
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='engagement')
    login_count = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    max_streak = models.PositiveIntegerField(default=0)
    last_login_date = models.DateField(null=True, blank=True)
    shown_message_ids = models.JSONField(default=list)  # No repetir mensajes
    
    class Meta:
        verbose_name = "Engagement de Usuario"

    @classmethod
    def get_or_create_for_user(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj
    def register_login(self):
        """Registra login y actualiza rachas."""
        from django.utils import timezone
        today = timezone.now().date()
        
        # ⚡ Si ya se registró hoy, no hacer nada
        if self.last_login_date == today:
            return {
                'is_first_login': False,
                'days_absent': 0,
                'login_count': self.login_count
            }
        
        is_first = self.login_count == 0
        days_absent = (today - self.last_login_date).days if self.last_login_date else 0
        
        # Actualizar racha
        if self.last_login_date:
            if days_absent == 1:
                self.current_streak += 1
            elif days_absent > 1:
                self.current_streak = 1
        else:
            self.current_streak = 1
        
        if self.current_streak > self.max_streak:
            self.max_streak = self.current_streak
        
        self.login_count += 1
        self.last_login_date = today
        self.save()
        
        return {'is_first_login': is_first, 'days_absent': days_absent, 'login_count': self.login_count}


# core/models.py

import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone

class DocumentoCompartido(models.Model):
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        blank=True,  # permite dejarlo vacío en el admin
    )

    titulo = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField(blank=True)

    

    archivo = models.FileField(
        upload_to="docs_compartidos/",
        storage=RawMediaCloudinaryStorage()
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_creados",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField(null=True, blank=True)

    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.titulo or 'Documento'} - {self.token[:8] if self.token else 'sin-token'}"

    @property
    def esta_expirado(self):
        if not self.activo:
            return True
        if self.expira_en and timezone.now() > self.expira_en:
            return True
        return False

    @classmethod
    def generar_token(cls):
        return secrets.token_urlsafe(32)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generar_token()
        super().save(*args, **kwargs)

