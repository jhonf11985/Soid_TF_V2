"""
Django settings for Soid_Tf_2 project.
Configuración segura para producción en Render.
"""
import os
from pathlib import Path

import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# SEGURIDAD - TODAS LAS CREDENCIALES EN VARIABLES DE ENTORNO
# =============================================================================

# En Render, configura estas variables en el Dashboard > Environment
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-cambiar-en-produccion")

# DEBUG automático: False en Render, True en local
DEBUG = os.environ.get("DEBUG", "1") == "1"

# Hosts permitidos
ALLOWED_HOSTS = [
    "soid-tf-v2.onrender.com",
    ".onrender.com",  # Permite subdominios de render
    "127.0.0.1",
    "localhost",
]

# En producción, añadir CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    "https://soid-tf-v2.onrender.com",
    "https://*.onrender.com",
]

# =============================================================================
# APLICACIONES
# =============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'miembros_app',
    'notificaciones_app',
    'votacion_app',
    'finanzas_app',
    'estructura_app',
    'nuevo_creyente_app',
    'actualizacion_datos_miembros',
    'django.contrib.humanize',
    "cloudinary",
    "cloudinary_storage",
    'inventario_app',
    'agenda_app',
    'evaluaciones_app',
    "codigo_qr",



]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # WhiteNoise ANTES de otros
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'miembros_app.signals.CurrentUserMiddleware',
]

ROOT_URLCONF = 'Soid_Tf_2.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.configuracion_global',
                'notificaciones_app.context_processors.notificaciones_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'Soid_Tf_2.wsgi.application'

# =============================================================================
# BASE DE DATOS
# =============================================================================

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# En Render, forzar SSL para PostgreSQL
if os.environ.get("RENDER"):
    DATABASES["default"]["OPTIONS"] = {"sslmode": "require"}

# =============================================================================
# VALIDACIÓN DE CONTRASEÑAS
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# INTERNACIONALIZACIÓN
# =============================================================================

LANGUAGE_CODE = 'en-us'  # Inglés para formato numérico con punto decimal
TIME_ZONE = 'America/Santo_Domingo'
USE_I18N = True
USE_TZ = True
USE_L10N = True
USE_THOUSAND_SEPARATOR = True

# =============================================================================
# CONFIGURACIÓN ESPECÍFICA DE LA APP
# =============================================================================

EDAD_MINIMA_MIEMBRO_OFICIAL = 14

# =============================================================================
# ARCHIVOS ESTÁTICOS (CSS, JavaScript, Imágenes)
# =============================================================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "core" / "static",
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

# =============================================================================
# ARCHIVOS MEDIA (fotos y archivos del usuario)
# =============================================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =============================================================================
# CLOUDINARY (MEDIA EN LA NUBE)
# =============================================================================

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    "API_KEY": os.environ.get("CLOUDINARY_API_KEY", ""),
    "API_SECRET": os.environ.get("CLOUDINARY_API_SECRET", ""),
}

# =============================================================================
# STORAGES - Django 5.x (reemplaza DEFAULT_FILE_STORAGE y STATICFILES_STORAGE)
# =============================================================================

# Determinar si usar Cloudinary (producción) o FileSystem (local)
_use_cloudinary = all([
    os.environ.get("CLOUDINARY_CLOUD_NAME"),
    os.environ.get("CLOUDINARY_API_KEY"),
    os.environ.get("CLOUDINARY_API_SECRET"),
])

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"
        if _use_cloudinary
        else "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# =============================================================================
# CONFIGURACIÓN DE CORREO (SMTP GMAIL)
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

# ⚠️ CREDENCIALES EN VARIABLES DE ENTORNO
# En Render Dashboard > Environment, añadir:
# EMAIL_HOST_USER = tu_email@gmail.com
# EMAIL_HOST_PASSWORD = tu_contraseña_de_app (16 caracteres)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# =============================================================================
# AUTENTICACIÓN
# =============================================================================

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# =============================================================================
# CHROME HEADLESS (para generación de PDFs)
# =============================================================================

RUNNING_IN_RENDER = os.environ.get("RENDER", None) is not None

if RUNNING_IN_RENDER:
    CHROME_PATH = "/usr/bin/chromium-browser"
else:
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# =============================================================================
# WEB PUSH NOTIFICATIONS (VAPID)
# =============================================================================

# ⚠️ CREDENCIALES EN VARIABLES DE ENTORNO
# En Render Dashboard > Environment, añadir:
# VAPID_PRIVATE_KEY = tu_clave_privada
# VAPID_PUBLIC_KEY = tu_clave_publica
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS_SUBJECT = os.environ.get("VAPID_CLAIMS_SUBJECT", "mailto:soidtf01@gmail.com")

# =============================================================================
# CONFIGURACIÓN ADICIONAL
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Seguridad adicional para producción
if not DEBUG:
    # HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Headers de seguridad
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

CRON_TOKEN = "soid_motor_secreto_2026"



