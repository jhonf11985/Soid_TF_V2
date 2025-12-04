from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max

from .models import Votacion, Ronda
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
    Al crearla, se genera automáticamente la Primera vuelta.
    """
    if request.method == "POST":
        form = VotacionForm(request.POST)
        if form.is_valid():
            votacion = form.save()

            # Crear PRIMERA VUELTA automática
            Ronda.objects.create(
                votacion=votacion,
                numero=1,
                nombre="Primera vuelta",
                estado=votacion.estado,  # normalmente BORRADOR
                fecha_inicio=votacion.fecha_inicio,
                fecha_fin=votacion.fecha_fin,
            )

            messages.success(request, "La votación se ha creado correctamente con su primera vuelta.")
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
    Muestra también las vueltas (rondas) asociadas.
    """
    votacion = get_object_or_404(Votacion, pk=pk)

    # Seguridad: si por alguna razón no tiene ninguna vuelta, crear la primera
    if not votacion.rondas.exists():
        Ronda.objects.create(
            votacion=votacion,
            numero=1,
            nombre="Primera vuelta",
            estado=votacion.estado,
            fecha_inicio=votacion.fecha_inicio,
            fecha_fin=votacion.fecha_fin,
        )

    if request.method == "POST":
        form = VotacionForm(request.POST, instance=votacion)
        if form.is_valid():
            votacion = form.save()

            # Opcional: sincronizar las fechas de la primera vuelta con la votación
            primera_ronda = votacion.rondas.order_by("numero").first()
            if primera_ronda:
                if not primera_ronda.fecha_inicio:
                    primera_ronda.fecha_inicio = votacion.fecha_inicio
                if not primera_ronda.fecha_fin:
                    primera_ronda.fecha_fin = votacion.fecha_fin
                primera_ronda.save()

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
def agregar_ronda(request, pk):
    """
    Crea una nueva vuelta (ronda) para una votación existente.
    Opción 1: se crea con número siguiente (2, 3, etc.).
    """
    votacion = get_object_or_404(Votacion, pk=pk)

    if request.method != "POST":
        return redirect("votacion:editar_votacion", pk=votacion.pk)

    ultimo_numero = votacion.rondas.aggregate(Max("numero"))["numero__max"] or 0
    nuevo_numero = ultimo_numero + 1

    Ronda.objects.create(
        votacion=votacion,
        numero=nuevo_numero,
        nombre=f"Vuelta {nuevo_numero}",
        estado=votacion.estado,  # normalmente BORRADOR o ABIERTA según la votación
    )

    messages.success(
        request,
        f"Se ha creado la vuelta {nuevo_numero} para esta elección."
    )
    return redirect("votacion:editar_votacion", pk=votacion.pk)


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

    # Crear primera vuelta para la nueva votación
    Ronda.objects.create(
        votacion=nueva_votacion,
        numero=1,
        nombre="Primera vuelta",
        estado=nueva_votacion.estado,
    )

    messages.success(
        request,
        f"Se ha creado una copia de la votación «{votacion_original.nombre}»."
    )
    return redirect("votacion:editar_votacion", pk=nueva_votacion.pk)


@login_required
def kiosko_ingreso_codigo(request):
    """
    Primera pantalla del modo kiosko:
    Ingreso del código de miembro (número de miembro).
    (Más adelante se conectará con la votación y vuelta activa).
    """
    return render(request, "votacion_app/kiosko_ingreso_codigo.html")


@login_required
def kiosko_seleccion_candidato(request):
    """
    Segunda pantalla del modo kiosko:
    Selección del candidato.
    (Luego conectaremos esto con la votación y la ronda actual).
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
