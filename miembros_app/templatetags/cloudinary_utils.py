# miembros_app/templatetags/cloudinary_tags.py
"""
Template tags personalizados para optimización de imágenes con Cloudinary.

Uso en templates:
    {% load cloudinary_tags %}
    
    {# Thumbnail optimizado (100x100, face detection, auto format/quality) #}
    {{ miembro.foto.url|cloudinary_thumb:'w_100,h_100,c_fill,g_face,f_auto,q_auto' }}
    
    {# O usando el tag con argumentos nombrados #}
    {% cloudinary_url miembro.foto width=100 height=100 crop='fill' gravity='face' %}
"""
import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def cloudinary_thumb(url, transformations='w_100,h_100,c_fill,g_face,f_auto,q_auto'):
    """
    Aplica transformaciones de Cloudinary a una URL de imagen.
    
    Args:
        url: URL original de Cloudinary (ej: https://res.cloudinary.com/xxx/image/upload/v123/foto.jpg)
        transformations: String con transformaciones (ej: 'w_100,h_100,c_fill,f_auto,q_auto')
    
    Returns:
        URL transformada con optimizaciones aplicadas
        
    Ejemplo:
        {{ m.foto.url|cloudinary_thumb:'w_100,h_100,c_fill,g_face,f_auto,q_auto' }}
        
        Entrada:  https://res.cloudinary.com/demo/image/upload/v1234/sample.jpg
        Salida:   https://res.cloudinary.com/demo/image/upload/w_100,h_100,c_fill,g_face,f_auto,q_auto/v1234/sample.jpg
    """
    if not url:
        return ''
    
    url = str(url)
    
    # Verificar si es una URL de Cloudinary
    if 'cloudinary.com' not in url and 'res.cloudinary' not in url:
        # No es Cloudinary, devolver la URL original
        return url
    
    # Patrón para URLs de Cloudinary
    # Formato: https://res.cloudinary.com/{cloud_name}/image/upload/{transformaciones_existentes?}/{version?}/{public_id}
    pattern = r'(https?://res\.cloudinary\.com/[^/]+/image/upload/)(v\d+/)?(.+)'
    match = re.match(pattern, url)
    
    if match:
        base_url = match.group(1)  # https://res.cloudinary.com/xxx/image/upload/
        version = match.group(2) or ''  # v1234/ o vacío
        public_id = match.group(3)  # foto.jpg o carpeta/foto.jpg
        
        # Construir URL con transformaciones
        return f"{base_url}{transformations}/{version}{public_id}"
    
    # Si no coincide el patrón, intentar otro formato común
    # https://res.cloudinary.com/{cloud}/image/upload/{public_id}
    pattern2 = r'(https?://res\.cloudinary\.com/[^/]+/image/upload/)(.+)'
    match2 = re.match(pattern2, url)
    
    if match2:
        base_url = match2.group(1)
        public_id = match2.group(2)
        return f"{base_url}{transformations}/{public_id}"
    
    # Si nada funciona, devolver URL original
    return url


@register.filter
def cloudinary_avatar(url, size=100):
    """
    Atajo para crear avatares optimizados.
    
    Aplica:
    - Recorte circular/cuadrado centrado en cara
    - Tamaño especificado
    - Formato automático (WebP/AVIF si el navegador soporta)
    - Calidad automática optimizada
    
    Ejemplo:
        {{ m.foto.url|cloudinary_avatar:80 }}
    """
    transformations = f'w_{size},h_{size},c_fill,g_face,f_auto,q_auto'
    return cloudinary_thumb(url, transformations)


@register.filter
def cloudinary_responsive(url, width=800):
    """
    Imagen responsive con ancho máximo.
    
    Ejemplo:
        {{ m.foto.url|cloudinary_responsive:600 }}
    """
    transformations = f'w_{width},c_limit,f_auto,q_auto'
    return cloudinary_thumb(url, transformations)


@register.simple_tag
def cloudinary_url(image_field, width=None, height=None, crop='fill', gravity='auto', 
                   quality='auto', format='auto', **extra_transforms):
    """
    Tag más flexible para generar URLs de Cloudinary con transformaciones.
    
    Ejemplo:
        {% cloudinary_url miembro.foto width=200 height=200 crop='fill' gravity='face' %}
        {% cloudinary_url miembro.foto width=400 crop='limit' %}
    """
    if not image_field:
        return ''
    
    url = str(image_field.url) if hasattr(image_field, 'url') else str(image_field)
    
    # Construir string de transformaciones
    transforms = []
    
    if width:
        transforms.append(f'w_{width}')
    if height:
        transforms.append(f'h_{height}')
    if crop:
        transforms.append(f'c_{crop}')
    if gravity and gravity != 'auto':
        transforms.append(f'g_{gravity}')
    if format:
        transforms.append(f'f_{format}')
    if quality:
        transforms.append(f'q_{quality}')
    
    # Agregar transformaciones extra
    for key, value in extra_transforms.items():
        transforms.append(f'{key}_{value}')
    
    transformation_string = ','.join(transforms)
    
    return cloudinary_thumb(url, transformation_string)


@register.inclusion_tag('miembros_app/components/optimized_image.html')
def optimized_image(image_field, alt='', css_class='', width=100, height=100, lazy=True):
    """
    Tag de inclusión que genera un <img> completo con lazy loading.
    
    Uso:
        {% optimized_image miembro.foto alt=miembro.nombres width=100 height=100 %}
    """
    if not image_field:
        return {'has_image': False, 'alt': alt}
    
    url = str(image_field.url) if hasattr(image_field, 'url') else str(image_field)
    
    # Generar URL optimizada
    transformations = f'w_{width},h_{height},c_fill,g_face,f_auto,q_auto'
    optimized_url = cloudinary_thumb(url, transformations)
    
    # Placeholder SVG inline (muy pequeño, carga instantáneo)
    placeholder = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}'%3E%3Crect fill='%23e5e7eb' width='{w}' height='{h}'/%3E%3C/svg%3E".format(
        w=width, h=height
    )
    
    return {
        'has_image': True,
        'src': placeholder if lazy else optimized_url,
        'data_src': optimized_url if lazy else '',
        'alt': alt,
        'css_class': f'{css_class} {"lazy-img" if lazy else ""}'.strip(),
        'width': width,
        'height': height,
        'lazy': lazy,
    }

@register.simple_tag
def foto_optimizada(image_field, w=200, h=200):
    if not image_field:
        return ''
    return cloudinary_url(image_field, width=w, height=h, crop='fill', gravity='face')
