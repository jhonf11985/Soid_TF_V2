from django.shortcuts import render
from .models import Module


def home(request):
    """
    Pantalla principal de Soid_Tf_2.
    Muestra solo los módulos activos, tipo Odoo.
    """
    modules = Module.objects.filter(is_enabled=True)

    context = {
        "modules": modules,
    }
    return render(request, "core/home.html", context)
