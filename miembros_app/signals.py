# ═══════════════════════════════════════════════════════════════════════════════
# miembros_app/signals.py
# Signals para registrar eventos automáticos en el Timeline
# ═══════════════════════════════════════════════════════════════════════════════

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Obtener usuario actual del request (thread-local)
# ═══════════════════════════════════════════════════════════════════════════════

# Para capturar el usuario en signals, usamos un middleware
# que guarda el request actual en thread-local storage

import threading

_thread_locals = threading.local()


def get_current_user():
    """Obtiene el usuario actual del request (si existe)."""
    return getattr(_thread_locals, 'user', None)


def get_current_request():
    """Obtiene el request actual (si existe)."""
    return getattr(_thread_locals, 'request', None)


class CurrentUserMiddleware:
    """
    Middleware para capturar el usuario actual en thread-local.
    
    Agregar a MIDDLEWARE en settings.py:
        'miembros_app.signals.CurrentUserMiddleware',
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        _thread_locals.user = getattr(request, 'user', None)
        response = self.get_response(request)
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNALS PARA MIEMBRO
# ═══════════════════════════════════════════════════════════════════════════════

@receiver(pre_save, sender='miembros_app.Miembro')
def miembro_pre_save(sender, instance, **kwargs):
    """
    Guarda el estado anterior del miembro antes de guardar.
    Esto permite comparar cambios en post_save.
    """
    if instance.pk:
        try:
            from miembros_app.models import Miembro
            old_instance = Miembro.objects.get(pk=instance.pk)
            instance._old_estado_miembro = old_instance.estado_miembro
            instance._old_activo = old_instance.activo
            instance._old_bautizado = old_instance.bautizado_confirmado
            instance._old_foto = old_instance.foto.name if old_instance.foto else None
            instance._old_etapa_actual = getattr(old_instance, 'etapa_actual', None)
        except sender.DoesNotExist:
            instance._old_estado_miembro = None
            instance._old_activo = None
            instance._old_bautizado = None
            instance._old_foto = None
            instance._old_etapa_actual = None
    else:
        # Es nuevo
        instance._old_estado_miembro = None
        instance._old_activo = None
        instance._old_bautizado = None
        instance._old_foto = None
        instance._old_etapa_actual = None


@receiver(post_save, sender='miembros_app.Miembro')
def miembro_post_save(sender, instance, created, **kwargs):
    """
    Registra eventos en el timeline después de guardar un miembro.
    """
    from miembros_app.models import TimelineEvent
    
    user = get_current_user()
    
    # ─────────────────────────────────────────────────────────────
    # EVENTO: Creación de miembro
    # ─────────────────────────────────────────────────────────────
    if created:
        TimelineEvent.registrar(
            miembro=instance,
            tipo='creacion',
            descripcion='Miembro registrado en el sistema',
            usuario=user,
        )
        return  # Si es nuevo, no hay cambios que comparar
    
    # ─────────────────────────────────────────────────────────────
    # EVENTO: Cambio de estado
    # ─────────────────────────────────────────────────────────────
    old_estado = getattr(instance, '_old_estado_miembro', None)
    new_estado = instance.estado_miembro
    
    if old_estado != new_estado and (old_estado or new_estado):
        # Obtener labels bonitos
        from miembros_app.models import ESTADO_MIEMBRO_CHOICES
        estados_dict = dict(ESTADO_MIEMBRO_CHOICES)
        
        old_label = estados_dict.get(old_estado, old_estado) or 'Sin estado'
        new_label = estados_dict.get(new_estado, new_estado) or 'Sin estado'
        
        TimelineEvent.registrar(
            miembro=instance,
            tipo='estado',
            descripcion='Cambio de estado del miembro',
            valor_anterior=old_label,
            valor_nuevo=new_label,
            usuario=user,
        )
    
    # ─────────────────────────────────────────────────────────────
    # EVENTO: Cambio de etapa
    # ─────────────────────────────────────────────────────────────
    old_etapa = getattr(instance, '_old_etapa_actual', None)
    new_etapa = getattr(instance, 'etapa_actual', None)
    
    if old_etapa != new_etapa and (old_etapa or new_etapa):
        from miembros_app.models import ETAPA_ACTUAL_CHOICES
        etapas_dict = dict(ETAPA_ACTUAL_CHOICES)
        
        old_label = etapas_dict.get(old_etapa, old_etapa) or 'Sin etapa'
        new_label = etapas_dict.get(new_etapa, new_etapa) or 'Sin etapa'
        
        TimelineEvent.registrar(
            miembro=instance,
            tipo='etapa',
            descripcion='Cambio de etapa del miembro',
            valor_anterior=old_label,
            valor_nuevo=new_label,
            usuario=user,
        )
    
    # ─────────────────────────────────────────────────────────────
    # EVENTO: Baja (activo → inactivo)
    # ─────────────────────────────────────────────────────────────
    old_activo = getattr(instance, '_old_activo', None)
    new_activo = instance.activo
    
    if old_activo is True and new_activo is False:
        razon = ''
        if instance.razon_salida:
            razon = str(instance.razon_salida)
        
        TimelineEvent.registrar(
            miembro=instance,
            tipo='baja',
            descripcion='Miembro dado de baja',
            detalle=f'Razón: {razon}' if razon else '',
            usuario=user,
        )
    
    # ─────────────────────────────────────────────────────────────
    # EVENTO: Reingreso (inactivo → activo)
    # ─────────────────────────────────────────────────────────────
    if old_activo is False and new_activo is True:
        TimelineEvent.registrar(
            miembro=instance,
            tipo='reingreso',
            descripcion='Miembro reincorporado',
            usuario=user,
        )
    
    # ─────────────────────────────────────────────────────────────
    # EVENTO: Bautismo registrado
    # ─────────────────────────────────────────────────────────────
    old_bautizado = getattr(instance, '_old_bautizado', None)
    new_bautizado = instance.bautizado_confirmado
    
    if not old_bautizado and new_bautizado:
        fecha_bautismo = ''
        if instance.fecha_bautismo:
            fecha_bautismo = instance.fecha_bautismo.strftime('%d/%m/%Y')
        
        TimelineEvent.registrar(
            miembro=instance,
            tipo='bautismo',
            descripcion='Registrado como bautizado',
            detalle=f'Fecha de bautismo: {fecha_bautismo}' if fecha_bautismo else '',
            usuario=user,
        )
    
    # ─────────────────────────────────────────────────────────────
    # EVENTO: Cambio de foto
    # ─────────────────────────────────────────────────────────────
    old_foto = getattr(instance, '_old_foto', None)
    new_foto = instance.foto.name if instance.foto else None
    
    if old_foto != new_foto and new_foto:
        TimelineEvent.registrar(
            miembro=instance,
            tipo='foto',
            descripcion='Foto de perfil actualizada',
            usuario=user,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNALS PARA UNIDADES (si el módulo está activo)
# ═══════════════════════════════════════════════════════════════════════════════

def registrar_asignacion_unidad(miembro, unidad, usuario=None):
    """Helper para registrar asignación a unidad desde cualquier parte."""
    from miembros_app.models import TimelineEvent
    
    TimelineEvent.registrar(
        miembro=miembro,
        tipo='unidad_asignada',
        descripcion=f'Asignado a {unidad}',
        referencia_tipo='unidad',
        usuario=usuario,
    )


def registrar_remocion_unidad(miembro, unidad, usuario=None):
    """Helper para registrar remoción de unidad desde cualquier parte."""
    from miembros_app.models import TimelineEvent
    
    TimelineEvent.registrar(
        miembro=miembro,
        tipo='unidad_removida',
        descripcion=f'Removido de {unidad}',
        referencia_tipo='unidad',
        usuario=usuario,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER PARA REGISTRAR ENVÍO DE EMAIL
# ═══════════════════════════════════════════════════════════════════════════════

def registrar_envio_email(miembro, asunto='', destinatario='', usuario=None):
    """
    Llamar esta función cuando se envíe un email al miembro.
    
    Ejemplo de uso en tu vista:
        from miembros_app.signals import registrar_envio_email
        
        # Después de enviar el email exitosamente:
        registrar_envio_email(
            miembro=miembro,
            asunto='Ficha de miembro',
            destinatario=miembro.email,
            usuario=request.user,
        )
    """
    from miembros_app.models import TimelineEvent
    
    TimelineEvent.registrar(
        miembro=miembro,
        tipo='email',
        descripcion=f'Correo enviado: {asunto}' if asunto else 'Correo enviado',
        detalle=f'Destinatario: {destinatario}' if destinatario else '',
        usuario=usuario,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER PARA REGISTRAR EVENTOS PERSONALIZADOS
# ═══════════════════════════════════════════════════════════════════════════════

def registrar_evento_personalizado(miembro, tipo, descripcion, detalle='', usuario=None, **kwargs):
    """
    Helper genérico para registrar cualquier evento desde las vistas.
    
    Ejemplo:
        from miembros_app.signals import registrar_evento_personalizado
        
        registrar_evento_personalizado(
            miembro=miembro,
            tipo='otro',
            descripcion='Visita pastoral realizada',
            detalle='Se visitó en su domicilio',
            usuario=request.user,
        )
    """
    from miembros_app.models import TimelineEvent
    
    return TimelineEvent.registrar(
        miembro=miembro,
        tipo=tipo,
        descripcion=descripcion,
        detalle=detalle,
        usuario=usuario,
        **kwargs,
    )