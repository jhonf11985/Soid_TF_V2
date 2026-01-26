# ═══════════════════════════════════════════════════════════════════════════════
# miembros_app/signals.py
# Signals para registrar eventos automáticos en el Timeline
# + Signals para relaciones familiares inteligentes
# ═══════════════════════════════════════════════════════════════════════════════

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 MENSAJES DE BIENVENIDA INTELIGENTES
# ═══════════════════════════════════════════════════════════════════════════════

from django.contrib.auth.signals import user_logged_in

@receiver(user_logged_in)
def on_user_login_welcome(sender, request, user, **kwargs):
    """Genera mensaje de bienvenida contextual."""
    print(f"🔔 SIGNAL: Usuario {user.username} ha iniciado sesión")
    
    try:
        from core.models import UserLoginHistory
        from core.services.welcome_messages import WelcomeMessageService
        
        previous = UserLoginHistory.register_login(user, request)
        
        # Determinar rol
        soid_ctx = {'rol': 'usuario'}
        if getattr(user, 'is_superuser', False):
            soid_ctx['rol'] = 'admin'
        else:
            try:
                groups = [g.name.lower() for g in user.groups.all()]
                if any("admin" in g or "geren" in g for g in groups):
                    soid_ctx['rol'] = 'admin'
                elif any("secre" in g for g in groups):
                    soid_ctx['rol'] = 'secretaria'
                elif any("lider" in g or "pastor" in g for g in groups):
                    soid_ctx['rol'] = 'lider'
            except:
                pass
        
        mensaje_data = WelcomeMessageService.get_welcome_message(
            user=user,
            previous_login=previous,
            soid_ctx=soid_ctx
        )
        
        request.session['welcome_message'] = mensaje_data
        request.session.modified = True
        print(f"   ✅ Mensaje: {mensaje_data.get('mensaje')[:40]}...")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Obtener usuario actual del request (thread-local)
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
#
#   🧠 RELACIONES FAMILIARES INTELIGENTES
#
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════


def _obtener_relaciones_directas(miembro_id, MiembroRelacion):
    """Obtiene relaciones directas normalizadas de un miembro."""
    padres = set()
    hijos = set()
    hermanos = set()
    conyuges = set()
    
    rels = (
        MiembroRelacion.objects
        .filter(Q(miembro_id=miembro_id) | Q(familiar_id=miembro_id))
        .filter(es_inferida=False)
        .select_related("miembro", "familiar")
    )
    
    for rel in rels:
        if rel.miembro_id == miembro_id:
            otro_id = rel.familiar_id
            tipo = rel.tipo_relacion
        else:
            otro_id = rel.miembro_id
            tipo = MiembroRelacion.inverse_tipo(rel.tipo_relacion, rel.miembro.genero)
        
        if tipo in ("padre", "madre"):
            padres.add(otro_id)
        elif tipo == "hijo":
            hijos.add(otro_id)
        elif tipo == "hermano":
            hermanos.add(otro_id)
        elif tipo == "conyuge":
            conyuges.add(otro_id)
    
    return {"padres": padres, "hijos": hijos, "hermanos": hermanos, "conyuges": conyuges}


def _obtener_padres_completos(miembro_id, MiembroRelacion):
    """Obtiene padres directos + inferidos (cónyuges de padres)."""
    rels = _obtener_relaciones_directas(miembro_id, MiembroRelacion)
    padres_directos = rels["padres"]
    padres_inferidos = set()
    
    if padres_directos:
        rels_padres = (
            MiembroRelacion.objects
            .filter(
                Q(miembro_id__in=padres_directos, tipo_relacion="conyuge") |
                Q(familiar_id__in=padres_directos, tipo_relacion="conyuge")
            )
            .filter(es_inferida=False)
        )
        
        for rel in rels_padres:
            conyuge_id = rel.familiar_id if rel.miembro_id in padres_directos else rel.miembro_id
            if conyuge_id not in padres_directos and conyuge_id != miembro_id:
                padres_inferidos.add(conyuge_id)
    
    return padres_directos, padres_inferidos


def _obtener_hijos_completos(miembro_id, MiembroRelacion):
    """Obtiene hijos directos + inferidos (hijos de cónyuge)."""
    rels = _obtener_relaciones_directas(miembro_id, MiembroRelacion)
    hijos_directos = rels["hijos"]
    conyuges = rels["conyuges"]
    hijos_inferidos = set()
    
    for conyuge_id in conyuges:
        rels_conyuge = _obtener_relaciones_directas(conyuge_id, MiembroRelacion)
        for hijo_id in rels_conyuge["hijos"]:
            if hijo_id not in hijos_directos and hijo_id != miembro_id:
                hijos_inferidos.add(hijo_id)
    
    return hijos_directos, hijos_inferidos


def _obtener_hermanos_completos(miembro_id, todos_padres, MiembroRelacion):
    """Obtiene hermanos (comparten al menos un padre)."""
    hermanos = set()
    
    if todos_padres:
        hermanos = set(
            MiembroRelacion.objects
            .filter(tipo_relacion__in=["padre", "madre"], familiar_id__in=todos_padres, es_inferida=False)
            .exclude(miembro_id=miembro_id)
            .values_list("miembro_id", flat=True)
        )
        
        hijos_de_padres = set(
            MiembroRelacion.objects
            .filter(miembro_id__in=todos_padres, tipo_relacion="hijo", es_inferida=False)
            .exclude(familiar_id=miembro_id)
            .values_list("familiar_id", flat=True)
        )
        hermanos |= hijos_de_padres
    
    return hermanos


@transaction.atomic
def sincronizar_relaciones_inferidas(miembro_id):
    """
    Calcula y guarda todas las relaciones inferidas de un miembro.
    Elimina las inferidas anteriores y crea las nuevas.
    """
    from miembros_app.models import MiembroRelacion, Miembro
    
    # 1) Eliminar relaciones inferidas anteriores de este miembro
    MiembroRelacion.objects.filter(
        miembro_id=miembro_id,
        es_inferida=True
    ).delete()
    
    # 2) Obtener relaciones directas
    rels = _obtener_relaciones_directas(miembro_id, MiembroRelacion)
    padres_directos = rels["padres"]
    hijos_directos = rels["hijos"]
    hermanos_directos = rels["hermanos"]
    conyuges_directos = rels["conyuges"]
    
    # 3) Calcular padres completos
    _, padres_inferidos = _obtener_padres_completos(miembro_id, MiembroRelacion)
    todos_padres = padres_directos | padres_inferidos
    
    # 4) Calcular hijos completos
    _, hijos_inferidos = _obtener_hijos_completos(miembro_id, MiembroRelacion)
    todos_hijos = hijos_directos | hijos_inferidos
    
    # 5) Calcular hermanos
    hermanos = _obtener_hermanos_completos(miembro_id, todos_padres, MiembroRelacion)
    hermanos |= hermanos_directos
    hermanos_solo_inferidos = hermanos - hermanos_directos
    
    # 6) Calcular abuelos (padres de mis padres)
    abuelos = set()
    for padre_id in todos_padres:
        p_dir, p_inf = _obtener_padres_completos(padre_id, MiembroRelacion)
        abuelos |= p_dir | p_inf
    
    # 7) Calcular tíos (hermanos de mis padres)
    tios = set()
    for padre_id in todos_padres:
        p_dir, p_inf = _obtener_padres_completos(padre_id, MiembroRelacion)
        abuelos_linea = p_dir | p_inf
        hermanos_padre = _obtener_hermanos_completos(padre_id, abuelos_linea, MiembroRelacion)
        tios |= hermanos_padre
    
    # 8) Calcular sobrinos (hijos de mis hermanos)
    sobrinos = set()
    for hermano_id in hermanos:
        h_dir, h_inf = _obtener_hijos_completos(hermano_id, MiembroRelacion)
        sobrinos |= h_dir | h_inf
    
    # 9) Calcular primos (hijos de mis tíos)
    primos = set()
    for tio_id in tios:
        h_dir, h_inf = _obtener_hijos_completos(tio_id, MiembroRelacion)
        primos |= h_dir | h_inf
    
    # 10) Calcular nietos (hijos de mis hijos)
    nietos = set()
    for hijo_id in todos_hijos:
        h_dir, h_inf = _obtener_hijos_completos(hijo_id, MiembroRelacion)
        nietos |= h_dir | h_inf
    
    # 11) Calcular cuñados
    cunados = set()
    for hermano_id in hermanos:
        r = _obtener_relaciones_directas(hermano_id, MiembroRelacion)
        cunados |= r["conyuges"]
    for conyuge_id in conyuges_directos:
        p_dir, p_inf = _obtener_padres_completos(conyuge_id, MiembroRelacion)
        padres_conyuge = p_dir | p_inf
        hermanos_conyuge = _obtener_hermanos_completos(conyuge_id, padres_conyuge, MiembroRelacion)
        cunados |= hermanos_conyuge
    
    # 12) Calcular suegros (padres de mi cónyuge)
    suegros = set()
    for conyuge_id in conyuges_directos:
        p_dir, p_inf = _obtener_padres_completos(conyuge_id, MiembroRelacion)
        suegros |= p_dir | p_inf
    
    # 13) Calcular yernos/nueras (cónyuges de mis hijos)
    yernos = set()
    for hijo_id in todos_hijos:
        r = _obtener_relaciones_directas(hijo_id, MiembroRelacion)
        yernos |= r["conyuges"]
    
    # 14) Calcular consuegros (padres de mis yernos)
    consuegros = set()
    for yerno_id in yernos:
        p_dir, p_inf = _obtener_padres_completos(yerno_id, MiembroRelacion)
        consuegros |= p_dir | p_inf
    
    # 15) Calcular bisabuelos (padres de mis abuelos)
    bisabuelos = set()
    for abuelo_id in abuelos:
        p_dir, p_inf = _obtener_padres_completos(abuelo_id, MiembroRelacion)
        bisabuelos |= p_dir | p_inf
    
    # 16) Calcular bisnietos (hijos de mis nietos)
    bisnietos = set()
    for nieto_id in nietos:
        h_dir, h_inf = _obtener_hijos_completos(nieto_id, MiembroRelacion)
        bisnietos |= h_dir | h_inf
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CREAR RELACIONES INFERIDAS
    # ═══════════════════════════════════════════════════════════════════════════
    
    ids_directos = padres_directos | hijos_directos | hermanos_directos | conyuges_directos
    
    todos_ids = (
        padres_inferidos | hijos_inferidos | hermanos_solo_inferidos | abuelos | tios |
        sobrinos | primos | nietos | cunados | suegros | yernos | consuegros |
        bisabuelos | bisnietos
    )
    
    miembros_map = {}
    for m in Miembro.objects.filter(id__in=todos_ids).only("id", "genero"):
        miembros_map[m.id] = m
    
    relaciones_a_crear = []
    
    def crear_relacion(otro_id, tipo, nota):
        if otro_id == miembro_id or otro_id in ids_directos:
            return
        existe = MiembroRelacion.objects.filter(
            miembro_id=miembro_id, familiar_id=otro_id
        ).exists()
        if not existe:
            relaciones_a_crear.append(MiembroRelacion(
                miembro_id=miembro_id,
                familiar_id=otro_id,
                tipo_relacion=tipo,
                es_inferida=True,
                notas=nota
            ))
    
    # Crear cada tipo de relación
    for otro_id in padres_inferidos:
        otro = miembros_map.get(otro_id)
        genero = (otro.genero or "").lower() if otro else ""
        tipo = "madre" if genero in ("f", "femenino", "mujer") else "padre"
        crear_relacion(otro_id, tipo, "Cónyuge de tu padre/madre")
    
    for otro_id in hijos_inferidos:
        crear_relacion(otro_id, "hijo", "Hijo/a de tu cónyuge")
    
    for otro_id in hermanos_solo_inferidos:
        crear_relacion(otro_id, "hermano", "Comparten padre/madre")
    
    for otro_id in abuelos:
        crear_relacion(otro_id, "abuelo", "Padre/madre de tu padre/madre")
    
    for otro_id in tios:
        crear_relacion(otro_id, "tio", "Hermano/a de tu padre/madre")
    
    for otro_id in sobrinos:
        crear_relacion(otro_id, "sobrino", "Hijo/a de tu hermano/a")
    
    for otro_id in primos:
        crear_relacion(otro_id, "primo", "Hijo/a de tu tío/a")
    
    for otro_id in nietos:
        crear_relacion(otro_id, "nieto", "Hijo/a de tu hijo/a")
    
    for otro_id in cunados:
        crear_relacion(otro_id, "cunado", "Cónyuge de hermano/a o hermano/a de cónyuge")
    
    for otro_id in suegros:
        crear_relacion(otro_id, "suegro", "Padre/madre de tu cónyuge")
    
    for otro_id in yernos:
        crear_relacion(otro_id, "yerno", "Cónyuge de tu hijo/a")
    
    for otro_id in consuegros:
        crear_relacion(otro_id, "consuegro", "Padre/madre del cónyuge de tu hijo/a")
    
    for otro_id in bisabuelos:
        crear_relacion(otro_id, "bisabuelo", "Padre/madre de tu abuelo/a")
    
    for otro_id in bisnietos:
        crear_relacion(otro_id, "bisnieto", "Hijo/a de tu nieto/a")
    
    # Guardar todas las relaciones
    if relaciones_a_crear:
        MiembroRelacion.objects.bulk_create(relaciones_a_crear)
    
    return len(relaciones_a_crear)


def sincronizar_familia_completa(miembro_id):
    """
    Sincroniza las relaciones de un miembro Y de todos sus familiares directos.
    """
    from miembros_app.models import MiembroRelacion
    
    ids_a_sincronizar = {miembro_id}
    
    rels = MiembroRelacion.objects.filter(
        Q(miembro_id=miembro_id) | Q(familiar_id=miembro_id),
        es_inferida=False
    )
    
    for rel in rels:
        ids_a_sincronizar.add(rel.miembro_id)
        ids_a_sincronizar.add(rel.familiar_id)
    
    total = 0
    for mid in ids_a_sincronizar:
        total += sincronizar_relaciones_inferidas(mid)
    
    return total


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNALS PARA RELACIONES FAMILIARES
# ═══════════════════════════════════════════════════════════════════════════════

# Flag para evitar recursión infinita
_sincronizando = threading.local()


@receiver(post_save, sender='miembros_app.MiembroRelacion')
def relacion_familiar_post_save(sender, instance, created, **kwargs):
    """Sincroniza relaciones inferidas cuando se guarda una relación directa."""
    if instance.es_inferida:
        return
    
    if getattr(_sincronizando, 'activo', False):
        return
    
    try:
        _sincronizando.activo = True
        sincronizar_familia_completa(instance.miembro_id)
        sincronizar_familia_completa(instance.familiar_id)
    finally:
        _sincronizando.activo = False


@receiver(post_delete, sender='miembros_app.MiembroRelacion')
def relacion_familiar_post_delete(sender, instance, **kwargs):
    """Sincroniza relaciones inferidas cuando se elimina una relación."""
    if instance.es_inferida:
        return
    
    if getattr(_sincronizando, 'activo', False):
        return
    
    try:
        _sincronizando.activo = True
        sincronizar_familia_completa(instance.miembro_id)
        sincronizar_familia_completa(instance.familiar_id)
    finally:
        _sincronizando.activo = False