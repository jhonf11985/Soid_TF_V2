from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Module, ConfiguracionSistema
from .forms import (
    ConfiguracionGeneralForm,
    ConfiguracionContactoForm,
    ConfiguracionReportesForm,
)


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
