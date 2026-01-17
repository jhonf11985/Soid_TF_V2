from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string
from .utils_email import enviar_correo_sencillo
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from .forms import UsuarioIglesiaForm
from . import ajax_views
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required

from .models import Module, ConfiguracionSistema
from .forms import (
    ConfiguracionGeneralForm,
    ConfiguracionContactoForm,
    ConfiguracionReportesForm,
)
from django.shortcuts import redirect
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.shortcuts import redirect
from miembros_app.models import Miembro
from django.db import transaction


from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required

User = get_user_model()

@login_required
def usuarios_listado(request):
    q = (request.GET.get("q") or "").strip()
    grupo_id = (request.GET.get("grupo") or "").strip()
    estado = (request.GET.get("estado") or "").strip()  # "activos" | "inactivos" | ""

    qs = User.objects.all().order_by("-date_joined")

    if q:
        qs = qs.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    if grupo_id.isdigit():
        qs = qs.filter(groups__id=int(grupo_id))

    if estado == "activos":
        qs = qs.filter(is_active=True)
    elif estado == "inactivos":
        qs = qs.filter(is_active=False)

    qs = qs.distinct()

    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    grupos = Group.objects.all().order_by("name")

    context = {
        "page_obj": page_obj,
        "q": q,
        "grupo_id": grupo_id,
        "estado": estado,
        "grupos": grupos,
    }
    return render(request, "core/usuarios/listado_usuarios.html", context)


def root_redirect(request):
    # Si ya está autenticado, lo mandamos al home (dashboard)
    if request.user.is_authenticated:
        return redirect("core:home")
    # Si no, al login
    return redirect("/accounts/login/")


# ✅ DEBE ESTAR AQUÍ ARRIBA
def es_staff(user):
    return user.is_staff or user.is_superuser


# =============================================================================
# TRADUCCIÓN DE PERMISOS AL ESPAÑOL
# =============================================================================

# Traducciones de acciones (verbos)
PERMISSION_ACTIONS = {
    'add': 'Crear',
    'change': 'Modificar',
    'delete': 'Eliminar',
    'view': 'Ver',
    'export': 'Exportar',
    'import': 'Importar',
    'print': 'Imprimir',
    'approve': 'Aprobar',
    'reject': 'Rechazar',
    'assign': 'Asignar',
    'manage': 'Gestionar',
    'access': 'Acceder',
    'list': 'Listar',
    'report': 'Reportar',
    'send': 'Enviar',
    'cancel': 'Cancelar',
    'close': 'Cerrar',
    'open': 'Abrir',
    'activate': 'Activar',
    'deactivate': 'Desactivar',
}

# Traducciones de modelos (sustantivos)
PERMISSION_MODELS = {
    # === Django Auth / Admin ===
    'user': 'usuario',
    'group': 'grupo',
    'permission': 'permiso',
    'logentry': 'entrada de log',
    'contenttype': 'tipo de contenido',
    'session': 'sesión',
    
    # === Core / Configuración ===
    'module': 'módulo',
    'configuracionsistema': 'configuración del sistema',
    'configuracion': 'configuración',
    
    # === Miembros ===
    'member': 'miembro',
    'miembro': 'miembro',
    'familia': 'familia',
    'family': 'familia',
    'memberphoto': 'foto de miembro',
    'memberdocument': 'documento de miembro',
    'memberhistory': 'historial de miembro',
    'estadocivil': 'estado civil',
    'nivelacademico': 'nivel académico',
    'profesion': 'profesión',
    'ocupacion': 'ocupación',
    'nacionalidad': 'nacionalidad',
    'tipomiembro': 'tipo de miembro',
    'estadomiembro': 'estado de miembro',
    'parentesco': 'parentesco',
    
    # === Estructura ===
    'church': 'iglesia',
    'iglesia': 'iglesia',
    'unit': 'unidad',
    'unidad': 'unidad',
    'unittype': 'tipo de unidad',
    'tipounidad': 'tipo de unidad',
    'role': 'rol',
    'rol': 'rol',
    'cargo': 'cargo',
    'position': 'cargo',
    'ministry': 'ministerio',
    'ministerio': 'ministerio',
    'department': 'departamento',
    'departamento': 'departamento',
    'zone': 'zona',
    'zona': 'zona',
    'district': 'distrito',
    'distrito': 'distrito',
    'sector': 'sector',
    'asignacionunidad': 'asignación de unidad',
    'unitassignment': 'asignación de unidad',
    
    # === Nuevo Creyente ===
    'nuevocreyente': 'nuevo creyente',
    'newbeliever': 'nuevo creyente',
    'seguimiento': 'seguimiento',
    'followup': 'seguimiento',
    'visitaseguimiento': 'visita de seguimiento',
    'consolidacion': 'consolidación',
    'discipulado': 'discipulado',
    
    # === Finanzas ===
    'diezmo': 'diezmo',
    'tithe': 'diezmo',
    'ofrenda': 'ofrenda',
    'offering': 'ofrenda',
    'donacion': 'donación',
    'donation': 'donación',
    'ingreso': 'ingreso',
    'income': 'ingreso',
    'egreso': 'egreso',
    'expense': 'egreso',
    'gasto': 'gasto',
    'presupuesto': 'presupuesto',
    'budget': 'presupuesto',
    'cuenta': 'cuenta',
    'account': 'cuenta',
    'transaccion': 'transacción',
    'transaction': 'transacción',
    'comprobante': 'comprobante',
    'receipt': 'comprobante',
    'categoria': 'categoría',
    'category': 'categoría',
    'tipotransaccion': 'tipo de transacción',
    'metodopago': 'método de pago',
    'paymentmethod': 'método de pago',
    
    # === Votación ===
    'election': 'elección',
    'eleccion': 'elección',
    'candidate': 'candidato',
    'candidato': 'candidato',
    'vote': 'voto',
    'voto': 'voto',
    'ballot': 'boleta',
    'boleta': 'boleta',
    'quorum': 'quórum',
    'votante': 'votante',
    'voter': 'votante',
    'resultado': 'resultado',
    'result': 'resultado',
    
    # === Actualización de Datos ===
    'solicitudactualizacion': 'solicitud de actualización',
    'updaterequest': 'solicitud de actualización',
    'cambiodatos': 'cambio de datos',
    'datachange': 'cambio de datos',
    
    # === Eventos / Asistencia ===
    'event': 'evento',
    'evento': 'evento',
    'attendance': 'asistencia',
    'asistencia': 'asistencia',
    'culto': 'culto',
    'service': 'culto',
    'actividad': 'actividad',
    'activity': 'actividad',
    'reunion': 'reunión',
    'meeting': 'reunión',
    
    # === Comunicación ===
    'mensaje': 'mensaje',
    'message': 'mensaje',
    'notificacion': 'notificación',
    'notification': 'notificación',
    'anuncio': 'anuncio',
    'announcement': 'anuncio',
    'email': 'correo electrónico',
    'sms': 'mensaje SMS',
}


def traducir_permiso(codename, name_original):
    """
    Traduce un permiso de Django al español.
    Ej: 'add_member' -> 'Crear miembro'
        'Can add member' -> 'Puede crear miembro'
    """
    codename_lower = codename.lower()
    
    # Intentar separar acción_modelo del codename
    parts = codename_lower.split('_', 1)
    
    if len(parts) == 2:
        action_code, model_code = parts
        
        # Buscar traducción de la acción
        action_es = PERMISSION_ACTIONS.get(action_code)
        
        # Buscar traducción del modelo (puede tener guiones bajos)
        model_clean = model_code.replace('_', '')
        model_es = PERMISSION_MODELS.get(model_code) or PERMISSION_MODELS.get(model_clean)
        
        if action_es and model_es:
            return f"{action_es} {model_es}"
        elif action_es:
            # Tenemos la acción pero no el modelo, capitalizar el modelo
            return f"{action_es} {model_code.replace('_', ' ')}"
    
    # Si no pudimos traducir, intentar traducir el nombre original
    # "Can add member" -> "Puede crear miembro"
    name_lower = name_original.lower()
    
    if name_lower.startswith('can '):
        rest = name_lower[4:]  # quitar "can "
        parts = rest.split(' ', 1)
        
        if len(parts) == 2:
            action_en, model_en = parts
            action_es = PERMISSION_ACTIONS.get(action_en)
            model_es = PERMISSION_MODELS.get(model_en.replace(' ', ''))
            
            if action_es and model_es:
                return f"Puede {action_es.lower()} {model_es}"
            elif action_es:
                return f"Puede {action_es.lower()} {model_en}"
    
    # Fallback: devolver el nombre original
    return name_original


class PermisoTraducido:
    """
    Wrapper para Permission que agrega el nombre traducido.
    """
    def __init__(self, permission):
        self._permission = permission
        self.id = permission.id
        self.codename = permission.codename
        self.name_original = permission.name
        self.name = traducir_permiso(permission.codename, permission.name)
    
    def __getattr__(self, name):
        return getattr(self._permission, name)


@login_required
@user_passes_test(es_staff)
def configuracion_permisos(request):
    """
    Pantalla para definir permisos por Roles (Groups) usando el sistema de permisos de Django,
    con soporte para Module.code en mayúsculas, nombres bonitos y variaciones.
    """

    User = get_user_model()

    # =========================================================
    # Roles
    # =========================================================
    roles = Group.objects.all().order_by("name")
    if not roles.exists():
        Group.objects.create(name="Administrador")
        roles = Group.objects.all().order_by("name")

    role_id = request.GET.get("role")
    role = Group.objects.filter(id=role_id).first() if role_id else roles.first()

    # =========================================================
    # Usuarios
    # =========================================================
    users = User.objects.all().order_by("first_name", "last_name", "username")

    # =========================================================
    # Resolver app_label desde Module.code
    # =========================================================
    installed_labels = set(app.split(".")[-1] for app in settings.INSTALLED_APPS)

    APP_LABEL_MAP = {
        # Miembros
        "miembros": "miembros_app",
        "miembros_app": "miembros_app",

        # Nuevo creyente
        "nuevo_creyente": "nuevo_creyente_app",
        "nuevo_creyente_app": "nuevo_creyente_app",

        # Finanzas
        "finanzas": "finanzas_app",
        "finanzas_app": "finanzas_app",

        # Estructura
        "estructura": "estructura_app",
        "estructura_app": "estructura_app",

        # Votación
        "votacion": "votacion_app",
        "votacion_app": "votacion_app",

        # Actualización de datos
        "actualizacion_datos_miembros": "actualizacion_datos_miembros",
        "actualizacion_datos": "actualizacion_datos_miembros",
        "actualizacion": "actualizacion_datos_miembros",

        # Configuración (core)
        "configuracion": "core",
        "core": "core",
    }
    

    def normalize(code: str) -> str:
        return (code or "").strip().lower().replace("-", "_").replace(" ", "_")

    def resolve_app_label(module_code: str) -> str:
        code = normalize(module_code)

        # 1) Mapa directo
        if code in APP_LABEL_MAP:
            return APP_LABEL_MAP[code]

        # 2) Coincidencia exacta con apps instalados
        if code in installed_labels:
            return code

        # 3) Probar code + "_app"
        candidate = f"{code}_app"
        if candidate in installed_labels:
            return candidate

        # 4) Heurística (ej: actualizacion_datos → actualizacion_datos_miembros)
        for lb in installed_labels:
            if code and (code in lb or lb in code):
                return lb

        # 5) Fallback
        return code

    # =========================================================
    # Módulos y permisos (con traducción)
    # =========================================================
    modules = Module.objects.all().order_by("order", "name")
    mod_perms = []

    for m in modules:
        app_label = resolve_app_label(m.code)

        perms_raw = Permission.objects.filter(
            content_type__app_label=app_label
        ).order_by("content_type__model", "codename")
        
        # Envolver cada permiso con la traducción
        perms_traducidos = [PermisoTraducido(p) for p in perms_raw]

        mod_perms.append({
            "module": m,
            "app_label": app_label,
            "perms": perms_traducidos,
            "pm_count": len(perms_traducidos),
        })

    # =========================================================
    # Guardar cambios
    # =========================================================
    if request.method == "POST":
        role_id_post = request.POST.get("role_id")
        role = Group.objects.filter(id=role_id_post).first() or role

        # Permisos
        perm_ids = request.POST.getlist("perm_ids")
        role.permissions.set(Permission.objects.filter(id__in=perm_ids))

        # Usuarios del rol
        selected_user_ids = set(request.POST.getlist("user_ids"))
        for u in users:
            if str(u.id) in selected_user_ids:
                u.groups.add(role)
            else:
                u.groups.remove(role)

        messages.success(
            request,
            f"Permisos y usuarios del rol «{role.name}» guardados correctamente."
        )
        return redirect(f"/configuracion/permisos/?role={role.id}")

    # =========================================================
    # Contexto
    # =========================================================
    context = {
        "roles": roles,
        "role": role,
        "users": users,
        "modules": modules,
        "mod_perms": mod_perms,
        "role_perm_ids": set(role.permissions.values_list("id", flat=True)),
        "role_user_ids": set(role.user_set.values_list("id", flat=True)),
    }

    return render(request, "core/configuracion_permisos.html", context)



@login_required(login_url="/accounts/login/")
def home(request):
    user = request.user

    # Superuser ve todo
    if user.is_superuser:
        modules = Module.objects.filter(is_enabled=True).order_by("order", "name")
        return render(request, "core/home.html", {"modules": modules})

    # Apps instalados (labels)
    installed_labels = set(app.split(".")[-1] for app in settings.INSTALLED_APPS)

    # Mapa para convertir Module.code -> app_label real de Django
    APP_LABEL_MAP = {
        "miembros": "miembros_app",
        "nuevo_creyente": "nuevo_creyente_app",
        "finanzas": "finanzas_app",
        "estructura": "estructura_app",
        "votacion": "votacion_app",
        "notificaciones": "notificaciones_app",
        "actualizacion_datos_miembros": "actualizacion_datos_miembros",
        "actualizacion_datos": "actualizacion_datos_miembros",
        "actualizacion": "actualizacion_datos_miembros",
        "configuracion": "core",
        "core": "core",
    }

    def normalize(code: str) -> str:
        return (code or "").strip().lower().replace("-", "_").replace(" ", "_")

    def resolve_app_label(module_code: str) -> str:
        code = normalize(module_code)

        if code in APP_LABEL_MAP:
            return APP_LABEL_MAP[code]

        if code in installed_labels:
            return code

        candidate = f"{code}_app"
        if candidate in installed_labels:
            return candidate

        for lb in installed_labels:
            if code and (code in lb or lb in code):
                return lb

        return code

    # Módulos activos
    active_modules = Module.objects.filter(is_enabled=True).order_by("order", "name")

    # Permisos del usuario (directos + por grupos/roles)
    user_perm_ids = set(user.user_permissions.values_list("id", flat=True))
    group_perm_ids = set(Permission.objects.filter(group__user=user).values_list("id", flat=True))
    all_perm_ids = user_perm_ids | group_perm_ids

    # App_labels donde el usuario tiene al menos un permiso de "ver"
    allowed_app_labels = set(
        Permission.objects.filter(
            id__in=all_perm_ids,
            codename__startswith="view_",
        ).values_list("content_type__app_label", flat=True)
    )

    # Mostrar solo módulos permitidos
    visible_modules = []
    for m in active_modules:
        app_label = resolve_app_label(m.code)
        if app_label in allowed_app_labels:
            visible_modules.append(m)

    return render(request, "core/home.html", {"modules": visible_modules})

@login_required
@user_passes_test(es_staff)
def configuracion_sistema(request):
    """
    Página principal de configuración: muestra tarjetas
    para acceder a cada tipo de configuración.
    """
    config = ConfiguracionSistema.load()
    context = {
        "config": config,
    }
    return render(request, "core/configuracion_sistema.html", context)


@login_required
@user_passes_test(es_staff)
def configuracion_general(request):
    """
    Configuración general: nombre, dirección, logo.
    """
    config = ConfiguracionSistema.load()

    if request.method == "POST":
        form = ConfiguracionGeneralForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración general guardada correctamente.")
            return redirect("core:configuracion_general")
        else:
            messages.error(request, "Hay errores en el formulario. Revisa los campos en rojo.")
    else:
        form = ConfiguracionGeneralForm(instance=config)

    context = {
        "form": form,
        "config": config,
    }
    return render(request, "core/configuracion_general.html", context)


@login_required
@user_passes_test(es_staff)
def configuracion_contacto(request):
    """
    Configuración de contacto y comunicación.
    """
    config = ConfiguracionSistema.load()

    if request.method == "POST":
        form = ConfiguracionContactoForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración de contacto guardada correctamente.")
            return redirect("core:configuracion_contacto")
        else:
            messages.error(request, "Hay errores en el formulario. Revisa los campos en rojo.")
    else:
        form = ConfiguracionContactoForm(instance=config)

    context = {
        "form": form,
        "config": config,
    }
    return render(request, "core/configuracion_contacto.html", context)


@login_required
@user_passes_test(es_staff)
def configuracion_reportes(request):
    """
    Parámetros de membresía y reportes.
    """
    config = ConfiguracionSistema.load()

    if request.method == "POST":
        form = ConfiguracionReportesForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Parámetros de reportes guardados correctamente.")
            return redirect("core:configuracion_reportes")
        else:
            messages.error(request, "Hay errores en el formulario. Revisa los campos en rojo.")
    else:
        form = ConfiguracionReportesForm(instance=config)

    context = {
        "form": form,
        "config": config,
    }
    return render(request, "core/configuracion_reportes.html", context)


@login_required
@user_passes_test(es_staff)
def probar_envio_correo(request):
    """
    Envía un correo de prueba usando la configuración SMTP actual (Zoho).
    """
    from django.core.mail import send_mail

    remitente = settings.EMAIL_HOST_USER

    asunto = "Prueba de correo desde Soid_Tf_2"
    mensaje = (
        "Hola,\n\n"
        "Este es un correo de prueba enviado usando Zoho SMTP y funciona correctamente.\n\n"
        "Si recibes este mensaje, todo está bien configurado.\n\n"
        "Bendiciones."
    )

    try:
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=remitente,
            recipient_list=[remitente],  # Envia a tu propia cuenta de Zoho
            fail_silently=False,
        )
        messages.success(
            request,
            f"Correo de prueba enviado correctamente a: {remitente}"
        )
    except Exception as e:
        messages.error(
            request,
            f"No se pudo enviar el correo: {e}"
        )

    return redirect("core:configuracion_contacto")


# =================================================
# CREAR USUARIO DESDE EL SISTEMA (SOLO ADMIN)
# =================================================
from django.views.decorators.csrf import ensure_csrf_cookie
@login_required
@permission_required('auth.add_user', raise_exception=True)
@ensure_csrf_cookie
def crear_usuario(request):
    if request.method == "POST":
        form = UsuarioIglesiaForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()

                miembro_id = form.cleaned_data.get("miembro_id")
                if miembro_id:
                    miembro = Miembro.objects.select_for_update().filter(
                        id=miembro_id,
                        usuario__isnull=True
                    ).first()

                    if miembro:
                        miembro.usuario = user
                        miembro.save()

            nombre_mostrar = user.get_full_name() or user.username
            messages.success(request, f"Usuario «{nombre_mostrar}» creado correctamente.")
            return redirect("core:listado")


    else:
        form = UsuarioIglesiaForm()

    return render(request, "core/usuarios/crear_usuario.html", {"form": form})




@login_required
def perfil_usuario(request):
    """
    Muestra información básica del usuario actual.
    """
    usuario = request.user
    context = {
        "usuario": usuario,
        "VAPID_PUBLIC_KEY": settings.VAPID_PUBLIC_KEY,
    }
    return render(request, "core/usuarios/perfil_usuario.html", context)
@login_required
def cambiar_contrasena(request):
    """
    Permite al usuario autenticado cambiar su contraseña.
    """
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Para que no se cierre la sesión al cambiar la contraseña
            update_session_auth_hash(request, user)
            messages.success(request, "Tu contraseña se ha actualizado correctamente.")
            return redirect("core:perfil_usuario")
        else:
            messages.error(request, "Hay errores en el formulario. Revisa los campos en rojo.")
    else:
        form = PasswordChangeForm(user=request.user)

    context = {
        "form": form,
    }
    return render(request, "core/usuarios/cambiar_contrasena.html", context)


@login_required
def cerrar_sesion(request):
    """
    Cierra la sesión del usuario y lo lleva a la pantalla de login.
    """
    logout(request)
    # Usamos la ruta definida en settings.LOGOUT_REDIRECT_URL
    return redirect(settings.LOGOUT_REDIRECT_URL)


# =============================================================================
# API: Detalle de miembro (para cargar foto y email en crear_usuario)
# =============================================================================

@login_required
def miembro_detalle_api(request, miembro_id):
    """
    Endpoint para obtener detalles de un miembro (foto, email, nombre, apellido)
    URL: /api/miembro-detalle/<int:miembro_id>/
    """
    try:
        miembro = Miembro.objects.get(id=miembro_id)
        
        # Construir URL de foto
        foto_url = None
        if miembro.foto:
            foto_url = miembro.foto.url
        
        return JsonResponse({
            'success': True,
            'id': miembro.id,
            'nombre': miembro.nombres or '',
            'apellido': miembro.apellidos or '',
            'email': miembro.email or '',
            'foto_url': foto_url,
        })
        
    except Miembro.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Miembro no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)