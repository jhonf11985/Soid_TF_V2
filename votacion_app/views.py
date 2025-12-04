from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from miembros_app.models import Miembro

from .models import Votacion, Ronda, Candidato
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
    - Configuración general (formulario VotacionForm)
    - Vueltas (rondas)
    - Selección de candidatos (misma pantalla)
    """
    votacion = get_object_or_404(Votacion, pk=pk)

    # Si por alguna razón no tiene ninguna vuelta, crear la primera
    if not votacion.rondas.exists():
        Ronda.objects.create(
            votacion=votacion,
            numero=1,
            nombre="Primera vuelta",
            estado=votacion.estado,
            fecha_inicio=votacion.fecha_inicio,
            fecha_fin=votacion.fecha_fin,
        )

    # ---- CANDIDATOS ACTUALES ----
    candidatos = (
        votacion.candidatos
        .select_related("miembro")
        .order_by("orden", "nombre")
    )

    # ---- BÚSQUEDA DE MIEMBROS PARA AGREGAR COMO CANDIDATOS ----
    q = request.GET.get("q", "").strip()

    # Base: solo miembros activos (usamos el campo 'activo' que aparece en el error)
    miembros_qs = Miembro.objects.filter(activo=True)

    # Edad mínima (si el modelo la tiene configurada)
    from datetime import date

    edad_minima = getattr(votacion, "edad_minima_candidato", None)
    if edad_minima:
        hoy = date.today()
        # Calculamos una fecha aproximada: hoy - edad_minima años
        try:
            fecha_tope = hoy.replace(year=hoy.year - edad_minima)
        except ValueError:
            # Por si cae en 29 de febrero
            fecha_tope = hoy.replace(
                year=hoy.year - edad_minima,
                month=2,
                day=28,
            )
        miembros_qs = miembros_qs.filter(fecha_nacimiento__lte=fecha_tope)

    # Búsqueda por texto: número, nombres, apellidos, código de miembro
    if q:
        miembros_qs = miembros_qs.filter(
            Q(numero_miembro__icontains=q) |
            Q(codigo_miembro__icontains=q) |
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q)
        )

    # Excluir miembros que ya SON candidatos en esta votación
    miembros_qs = miembros_qs.exclude(candidaturas__votacion=votacion)

    # Limitar la lista por rendimiento
    miembros_qs = miembros_qs.order_by("numero_miembro", "id")[:50]

    # ---- POST: saber qué acción se está haciendo ----
    if request.method == "POST":
        accion = request.POST.get("accion")

        # 1) Guardar configuración de la votación
        if accion == "guardar_votacion":
            form = VotacionForm(request.POST, instance=votacion)
            if form.is_valid():
                votacion = form.save()

                # Opcional: sincronizar fechas de la primera vuelta
                primera_ronda = votacion.rondas.order_by("numero").first()
                if primera_ronda:
                    if not primera_ronda.fecha_inicio:
                        primera_ronda.fecha_inicio = votacion.fecha_inicio
                    if not primera_ronda.fecha_fin:
                        primera_ronda.fecha_fin = votacion.fecha_fin
                    primera_ronda.save()

                messages.success(request, "La votación se ha actualizado correctamente.")
                return redirect("votacion:editar_votacion", pk=votacion.pk)

        # 2) Agregar candidato desde la lista de miembros
        elif accion == "agregar_candidato":
            miembro_id = request.POST.get("miembro_id")
            if miembro_id:
                miembro = get_object_or_404(Miembro, pk=miembro_id)

                ya_existe = Candidato.objects.filter(
                    votacion=votacion,
                    miembro=miembro,
                ).exists()

                if ya_existe:
                    messages.warning(
                        request,
                        "Este miembro ya está registrado como candidato en esta elección."
                    )
                else:
                    # Usamos el __str__ del miembro como nombre visible del candidato
                    nombre_candidato = str(miembro)
                    Candidato.objects.create(
                        votacion=votacion,
                        miembro=miembro,
                        nombre=nombre_candidato,
                    )
                    messages.success(
                        request,
                        f"Se ha añadido a «{nombre_candidato}» como candidato."
                    )

            return redirect("votacion:editar_votacion", pk=votacion.pk)

        # Si no hay acción clara, tratamos como guardar votación por defecto
        form = VotacionForm(request.POST, instance=votacion)
    else:
        form = VotacionForm(instance=votacion)

    contexto = {
        "form": form,
        "titulo": f"Configurar votación: {votacion.nombre}",
        "es_nueva": False,
        "votacion": votacion,
        "candidatos": candidatos,
        "miembros": miembros_qs,
        "q": q,
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

@login_required
def gestionar_candidatos(request, pk):
    """
    Pantalla para seleccionar candidatos de una votación.
    - Muestra candidatos actuales.
    - Permite buscar miembros (por código, nombre, etc.)
      y agregarlos como candidatos.
    - Solo muestra miembros activos y, si se define, mayores
      o iguales a la edad mínima de la votación.
    """
    votacion = get_object_or_404(Votacion, pk=pk)

    # ---- Candidatos actuales de esta elección ----
    candidatos = (
        votacion.candidatos
        .select_related("miembro")
        .order_by("orden", "nombre")
    )

    # ---- Búsqueda de miembros potenciales ----
    q = request.GET.get("q", "").strip()
    miembros_qs = Miembro.objects.all()

    # 🟢 FILTRO: solo miembros activos (AJUSTA a tu modelo)
    # Ejemplo si tienes un campo 'estado' o 'es_activo':
    # miembros_qs = miembros_qs.filter(estado="ACTIVO")
    # o:
    # miembros_qs = miembros_qs.filter(activo=True)

    # 🟢 FILTRO: edad mínima (AJUSTA a tus campos)
    if votacion.edad_minima_candidato:
        # Aquí depende de cómo tengas guardada la fecha de nacimiento.
        # EJEMPLO si tienes 'fecha_nacimiento' en Miembro:
        #
        # from datetime import date, timedelta
        # from dateutil.relativedelta import relativedelta
        #
        # hoy = date.today()
        # fecha_tope = hoy - relativedelta(years=votacion.edad_minima_candidato)
        # miembros_qs = miembros_qs.filter(fecha_nacimiento__lte=fecha_tope)
        #
        # Si ya tienes una propiedad 'edad' calculada,
        # puedes filtrar en Python después (no en la BD).
        pass

    # 🟢 Búsqueda por texto (AJUSTA a tus campos):
    if q:
        miembros_qs = miembros_qs.filter(
            Q(nombre__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(id__icontains=q)  # o código de miembro si tienes un campo específico
        )

    # 🟢 Excluir miembros que ya son candidatos en esta votación
    miembros_qs = miembros_qs.exclude(candidaturas__votacion=votacion)

    # Limitar un poco la lista para no cargar demasiados
    miembros_qs = miembros_qs.order_by("id")[:50]

    # ---- POST: agregar candidato desde la lista ----
    if request.method == "POST":
        miembro_id = request.POST.get("miembro_id")
        if miembro_id:
            miembro = get_object_or_404(Miembro, pk=miembro_id)

            # Evitar duplicados por seguridad
            ya_existe = Candidato.objects.filter(
                votacion=votacion,
                miembro=miembro
            ).exists()

            if ya_existe:
                messages.warning(
                    request,
                    "Este miembro ya está registrado como candidato en esta elección."
                )
            else:
                # Aquí puedes ajustar cómo se construye el nombre visible del candidato
                nombre_candidato = str(miembro)
                # por ejemplo: nombre_candidato = miembro.nombre_completo

                Candidato.objects.create(
                    votacion=votacion,
                    miembro=miembro,
                    nombre=nombre_candidato,
                )
                messages.success(
                    request,
                    f"Se ha añadido a «{nombre_candidato}» como candidato."
                )

            return redirect("votacion:gestionar_candidatos", pk=votacion.pk)

    contexto = {
        "votacion": votacion,
        "candidatos": candidatos,
        "miembros": miembros_qs,
        "q": q,
    }
    return render(request, "votacion_app/votacion_candidatos.html", contexto)
