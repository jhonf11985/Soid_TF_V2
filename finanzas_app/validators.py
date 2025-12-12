# finanzas_app/validators.py

from django.core.exceptions import ValidationError
import mimetypes
from django.db import models


# Tipos MIME permitidos
TIPOS_PERMITIDOS = {
    # Imágenes
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/webp': ['.webp'],
    
    # Documentos
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'text/csv': ['.csv'],
}

# Tamaño máximo por archivo: 10MB
TAMAÑO_MAXIMO_ARCHIVO = 10 * 1024 * 1024  # 10MB en bytes

# Tamaño máximo total por movimiento: 50MB
TAMAÑO_MAXIMO_TOTAL = 50 * 1024 * 1024  # 50MB en bytes


def validar_archivo(archivo):
    """
    Valida que un archivo cumpla con los requisitos de seguridad.
    
    Params:
        archivo: UploadedFile de Django
    
    Raises:
        ValidationError si el archivo no es válido
    """
    # Validar tamaño
    if archivo.size > TAMAÑO_MAXIMO_ARCHIVO:
        tamaño_mb = TAMAÑO_MAXIMO_ARCHIVO / (1024 * 1024)
        raise ValidationError(
            f"El archivo es demasiado grande. Tamaño máximo: {tamaño_mb}MB"
        )
    
    # Validar extensión
    nombre = archivo.name.lower()
    extension = None
    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv']:
        if nombre.endswith(ext):
            extension = ext
            break
    
    if not extension:
        raise ValidationError(
            "Tipo de archivo no permitido. "
            "Formatos válidos: PDF, imágenes (JPG, PNG, GIF, WEBP), documentos (DOC, DOCX, XLS, XLSX, CSV)"
        )
    
    # Validar tipo MIME
    tipo_mime = archivo.content_type
    if tipo_mime not in TIPOS_PERMITIDOS:
        # Intentar adivinar por extensión
        tipo_mime_adivinado, _ = mimetypes.guess_type(archivo.name)
        if tipo_mime_adivinado and tipo_mime_adivinado in TIPOS_PERMITIDOS:
            tipo_mime = tipo_mime_adivinado
        else:
            raise ValidationError(
                f"Tipo de archivo no permitido: {tipo_mime}"
            )
    
    # Verificar que la extensión coincida con el tipo MIME
    extensiones_validas = TIPOS_PERMITIDOS.get(tipo_mime, [])
    if extension not in extensiones_validas:
        raise ValidationError(
            "La extensión del archivo no coincide con su tipo."
        )
    
    return True


def validar_tamaño_total(movimiento, nuevo_tamaño=0):
    """
    Valida que el tamaño total de adjuntos no exceda el límite.
    
    Params:
        movimiento: MovimientoFinanciero
        nuevo_tamaño: int, tamaño del nuevo archivo a agregar
    
    Raises:
        ValidationError si se excede el límite
    """
    from .models import AdjuntoMovimiento
    
    tamaño_actual = AdjuntoMovimiento.objects.filter(
        movimiento=movimiento
    ).aggregate(
        total=models.Sum('tamaño')
    )['total'] or 0
    
    tamaño_total = tamaño_actual + nuevo_tamaño
    
    if tamaño_total > TAMAÑO_MAXIMO_TOTAL:
        limite_mb = TAMAÑO_MAXIMO_TOTAL / (1024 * 1024)
        actual_mb = tamaño_total / (1024 * 1024)
        raise ValidationError(
            f"Se excede el límite de almacenamiento para este movimiento. "
            f"Límite: {limite_mb}MB, Actual: {actual_mb:.1f}MB"
        )
    
    return True