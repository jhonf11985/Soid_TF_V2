from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Votacion
from .forms import VotacionForm


@login_required
def lista_votaciones(request):
    """
    Lista de todas las votaciones.
    """
    votaciones = Votacion.objects.all()
    return render(
        request,
        "votacion_app/lista_votaciones.html",
        {"votaciones": votaciones},
    )


@login_required
def crear_votacion(request):
    """
    Pantalla de configuración para crear una nueva votación.
    """
    if request.method == "POST":
        form = VotacionForm(request.POST)
        if form.is_valid():
            votacion = form.save()
            messages.success(request, "La votación se ha creado correctamente.")
            return redirect("votacion:editar_votacion", pk=votacion.pk)
    else:
        form = VotacionForm()

    contexto = {
        "form": form,
        "titulo": "Crear votación",
        "es_nueva": True,
        "votacion": None,
    }
    return render(request, "votacion_app/votacion_configuracion.html", contexto)


@login_required
def editar_votacion(request, pk):
    """
    Pantalla de configuración para editar una votación existente.
    """
    votacion = get_object_or_404(Votacion, pk=pk)

    if request.method == "POST":
        form = VotacionForm(request.POST, instance=votacion)
        if form.is_valid():
            form.save()
            messages.success(request, "La votación se ha actualizado correctamente.")
            return redirect("votacion:editar_votacion", pk=votacion.pk)
    else:
        form = VotacionForm(instance=votacion)

    contexto = {
        "form": form,
        "titulo": f"Configurar votación: {votacion.nombre}",
        "es_nueva": False,
        "votacion": votacion,
    }
    return render(request, "votacion_app/votacion_configuracion.html", contexto)


@login_required
def duplicar_votacion(request, pk):
    """
    Duplica una votación (sin votos), incluyendo sus candidatos.
    Deja la nueva votación en estado BORRADOR.
    """
    votacion_original = get_object_or_404(Votacion, pk=pk)

    # Solo aceptamos POST para evitar duplicar desde un simple enlace GET
    if request.method != "POST":
        return redirect("votacion:editar_votacion", pk=votacion_original.pk)

    # Crear la nueva votación copiando campos clave
    nueva_votacion = Votacion.objects.create(
        nombre=f"{votacion_original.nombre} (copia)",
        descripcion=votacion_original.descripcion,
        tipo=votacion_original.tipo,
        estado="BORRADOR",  # siempre borrador al duplicar
        total_habilitados=votacion_original.total_habilitados,
        quorum_minimo=votacion_original.quorum_minimo,
        regla_ganador=votacion_original.regla_ganador,
        numero_cargos=votacion_original.numero_cargos,
        permite_empates=votacion_original.permite_empates,
        permite_voto_remoto=votacion_original.permite_voto_remoto,
        observaciones_internas=votacion_original.observaciones_internas,
        # No copiamos fechas de inicio/fin para evitar confusiones
        fecha_inicio=None,
        fecha_fin=None,
    )

    # Duplicar candidatos (sin votos)
    for candidato in votacion_original.candidatos.all():
        candidato.pk = None  # hace que se cree un nuevo registro
        candidato.votacion = nueva_votacion
        candidato.save()

    messages.success(
        request,
        f"Se ha creado una copia de la votación «{votacion_original.nombre}».",
    )
    return redirect("votacion:editar_votacion", pk=nueva_votacion.pk)


@login_required
def kiosko_ingreso_codigo(request):
    """
    Primera pantalla del modo kiosko:
    Ingreso del código de miembro (número de miembro).
    """
    return render(request, "votacion_app/kiosko_ingreso_codigo.html")


@login_required
def kiosko_seleccion_candidato(request):
    """
    Segunda pantalla del modo kiosko:
    Selección del candidato.
    (Luego conectaremos esto con la votación activa).
    """
    return render(request, "votacion_app/kiosko_seleccion_candidato.html")


@login_required
def kiosko_confirmacion(request):
    """
    Tercera pantalla del modo kiosko:
    Confirmación del voto.
    """
    return render(request, "votacion_app/kiosko_confirmacion.html")

@login_required
def eliminar_votacion(request, pk):
    """
    Elimina una votación SOLO si no tiene votos.
    Se usa POST para evitar eliminaciones accidentales.
    """
    votacion = get_object_or_404(Votacion, pk=pk)

    # Seguridad: si tiene votos, no se puede eliminar
    if votacion.votos.exists():
        messages.error(
            request,
            "No se puede eliminar esta votación porque ya tiene votos registrados."
        )
        return redirect("votacion:editar_votacion", pk=votacion.pk)

    if request.method == "POST":
        nombre = votacion.nombre
        votacion.delete()
        messages.success(request, f"La votación «{nombre}» se ha eliminado correctamente.")
        return redirect("votacion:lista_votaciones")

    # Si entra por GET, lo llevamos a configuración
    return redirect("votacion:editar_votacion", pk=votacion.pk)

