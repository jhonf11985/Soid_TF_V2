from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


from miembros_app.models import Miembro
from estructura_app.models import UnidadMembresia

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from estructura_app.models import UnidadMembresia

@login_required
def dashboard(request):
    # ✅ Solo usuarios vinculados a un Miembro pueden entrar al portal
    if not hasattr(request.user, "miembro") or request.user.miembro is None:
        messages.error(request, "Tu usuario no está vinculado a un miembro. Contacta al administrador.")
        # Cambia este redirect por el destino que tú quieras:
        return redirect("login")  # o "core:home" / "admin:index"

    miembro = request.user.miembro

    unidad_nombre = None
    lider_nombre = None

    membresia = (
        UnidadMembresia.objects
        .select_related("unidad")
        .filter(miembo_fk=miembro, activo=True)
        .first()
    )

    if membresia:
        unidad_nombre = membresia.unidad.nombre

        lider = (
            UnidadMembresia.objects
            .select_related("miembo_fk", "rol")
            .filter(unidad=membresia.unidad, activo=True, rol__tipo="LIDERAZGO")
            .exclude(miembo_fk=miembro)
            .first()
        )
        if lider:
            lider_nombre = f"{lider.miembo_fk.nombres} {lider.miembo_fk.apellidos}"

    context = {
        "miembro": miembro,
        "unidad_nombre": unidad_nombre,
        "lider_nombre": lider_nombre,
    }
    return render(request, "portal_miembros/dashboard.html", context)

@login_required
def perfil(request):
    return render(request, "portal_miembros/perfil.html")


@login_required
def notificaciones(request):
    return render(request, "portal_miembros/notificaciones.html")
