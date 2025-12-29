from django.shortcuts import render, redirect
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

def root_redirect(request):
    # Si ya está autenticado, lo mandamos al home (dashboard)
    if request.user.is_authenticated:
        return redirect("core:home")
    # Si no, al login
    return redirect("/accounts/login/")


@login_required(login_url="/accounts/login/")
def home(request):
    """
    Pantalla principal de Soid_Tf_2.
    Muestra solo los módulos activos, tipo Odoo.
    """
    modules = Module.objects.filter(is_enabled=True)
    context = {"modules": modules}
    return render(request, "core/home.html", context)

def es_staff(user):
    return user.is_staff or user.is_superuser


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
@login_required
@permission_required('auth.add_user', raise_exception=True)
def crear_usuario(request):
    if request.method == "POST":
        form = UsuarioIglesiaForm(request.POST)
        if form.is_valid():
            user = form.save()
            nombre_mostrar = user.get_full_name() or user.username
            messages.success(request, f"Usuario «{nombre_mostrar}» creado correctamente.")
            return redirect("core:home")
    else:
        form = UsuarioIglesiaForm()

    context = {
        "form": form,
    }
    return render(request, "core/usuarios/crear_usuario.html", context)

@login_required
def perfil_usuario(request):
    """
    Muestra información básica del usuario actual.
    """
    usuario = request.user
    context = {
        "usuario": usuario,
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
