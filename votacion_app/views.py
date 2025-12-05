from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q, Max
from django.urls import reverse
from django.http import HttpResponseRedirect

from miembros_app.models import Miembro
from .models import Votacion, Ronda, Candidato, Voto
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
    
    # Para controlar qué pestaña debe quedar activa al recargar
    tab_activa = None


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

    # Candidatos actuales
    candidatos = (
        votacion.candidatos
        .select_related("miembro")
        .order_by("orden", "nombre")
    )

    # Ya no usamos lista masiva de miembros
    q = ""
    miembros_qs = None

    # Para el modal de confirmación / errores de candidato
    pre_candidato = None
    codigo_pre_candidato = None
    candidato_error = None

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

        # 2) PREVISUALIZAR candidato por código (mostrar modal o error)
        elif accion == "previsualizar_candidato":
            sufijo = request.POST.get("codigo_sufijo", "").strip()

            if not sufijo:
                candidato_error = (
                    "Debes introducir el número del código de miembro. "
                    "Ejemplo: 12 o 0012."
                )
            else:
                # Normalizamos lo que escriban: 12, 0012, TF-0012, tf0012…
                sufijo_upper = sufijo.upper()
                if sufijo_upper.startswith("TF-"):
                    codigo_busqueda = sufijo_upper
                else:
                    limpio = sufijo_upper.replace("TF", "").replace("-", "")
                    limpio = limpio.zfill(4)   # 12 -> 0012
                    codigo_busqueda = f"TF-{limpio}"

                try:
                    # Traemos el miembro por código
                    miembro = Miembro.objects.get(codigo_miembro__iexact=codigo_busqueda)
                except Miembro.DoesNotExist:
                    candidato_error = (
                        f"No se encontró ningún miembro con el código {codigo_busqueda}."
                    )
                else:
                    # REGLA 1: debe ser miembro oficial (tener estado_miembro)
                    if not miembro.estado_miembro:
                        candidato_error = (
                            "Este miembro no puede ser elegido como candidato porque aún "
                            "no es miembro oficial (menor de la edad mínima del sistema "
                            "de membresía)."
                        )
                    # REGLA 2: estado_miembro debe ser ACTIVO
                    elif miembro.estado_miembro != "activo":
                        candidato_error = (
                            "Este miembro no puede ser elegido como candidato porque su "
                            "estado no es ACTIVO."
                        )
                    else:
                        # REGLA 3 (opcional): edad mínima específica de esta votación
                        edad_minima_vot = getattr(
                            votacion,
                            "edad_minima_candidato",
                            None,
                        )
                        if edad_minima_vot:
                            # Usamos el método calcular_edad del modelo Miembro
                            edad = (
                                miembro.calcular_edad()
                                if hasattr(miembro, "calcular_edad")
                                else None
                            )
                            if edad is None or edad < edad_minima_vot:
                                candidato_error = (
                                    "Este miembro no puede ser elegido como candidato "
                                    f"porque no cumple la edad mínima de "
                                    f"{edad_minima_vot} años para esta elección."
                                )
                            else:
                                # Pasa reglas; verificamos duplicado
                                ya_existe = Candidato.objects.filter(
                                    votacion=votacion,
                                    miembro=miembro,
                                ).exists()
                                if ya_existe:
                                    candidato_error = (
                                        f"El miembro con código {codigo_busqueda} ya "
                                        "figura como candidato en esta elección."
                                    )
                                else:
                                    pre_candidato = miembro
                                    codigo_pre_candidato = codigo_busqueda
                        else:
                            # Sin edad mínima específica, solo estado_miembro
                            ya_existe = Candidato.objects.filter(
                                votacion=votacion,
                                miembro=miembro,
                            ).exists()
                            if ya_existe:
                                candidato_error = (
                                    f"El miembro con código {codigo_busqueda} ya "
                                    "figura como candidato en esta elección."
                                )
                            else:
                                pre_candidato = miembro
                                codigo_pre_candidato = codigo_busqueda

            # Re-renderizamos la página (sin redirect) para que se vea el modal o el error
            form = VotacionForm(instance=votacion)
            tab_activa = "candidatos"

        # 3) CONFIRMAR y crear candidato (desde el modal)
        elif accion == "agregar_candidato_confirmado":
            codigo_confirmado = request.POST.get("codigo_miembro", "").strip()
            if not codigo_confirmado:
                messages.error(request, "No se recibió un código de miembro válido.")
                return redirect("votacion:editar_votacion", pk=votacion.pk)

            codigo_confirmado = codigo_confirmado.upper()

            try:
                miembro = Miembro.objects.get(codigo_miembro__iexact=codigo_confirmado)
            except Miembro.DoesNotExist:
                messages.error(
                    request,
                    f"No se encontró ningún miembro con el código {codigo_confirmado}.",
                )
                return redirect("votacion:editar_votacion", pk=votacion.pk)

            # Validaciones de seguridad (por si cambió algo desde la previsualización)

            # REGLA 1: miembro oficial
            if not miembro.estado_miembro:
                messages.error(
                    request,
                    "Este miembro no puede ser elegido como candidato porque aún no es "
                    "miembro oficial.",
                )
                return redirect("votacion:editar_votacion", pk=votacion.pk)

            # REGLA 2: estado activo
            if miembro.estado_miembro != "activo":
                messages.error(
                    request,
                    "Este miembro no puede ser elegido como candidato porque su estado "
                    "no es ACTIVO.",
                )
                return redirect("votacion:editar_votacion", pk=votacion.pk)

            # REGLA 3 (opcional): edad mínima de la votación
            edad_minima_vot = getattr(votacion, "edad_minima_candidato", None)
            if edad_minima_vot:
                edad = (
                    miembro.calcular_edad()
                    if hasattr(miembro, "calcular_edad")
                    else None
                )
                if edad is None or edad < edad_minima_vot:
                    messages.error(
                        request,
                        "Este miembro no puede ser elegido como candidato porque no "
                        f"cumple la edad mínima de {edad_minima_vot} años para esta "
                        "elección.",
                    )
                    return redirect("votacion:editar_votacion", pk=votacion.pk)

            # Evitar duplicados
            ya_existe = Candidato.objects.filter(
                votacion=votacion,
                miembro=miembro,
            ).exists()

            if ya_existe:
                messages.warning(
                    request,
                    f"El miembro con código {codigo_confirmado} ya figura como candidato "
                    "en esta elección.",
                )
            else:
                nombre_candidato = str(miembro)
                Candidato.objects.create(
                    votacion=votacion,
                    miembro=miembro,
                    nombre=nombre_candidato,
                )
                messages.success(
                    request,
                    f"Se ha añadido a «{nombre_candidato}» (código {codigo_confirmado}) "
                    "como candidato.",
                )

            url_candidatos = (
                reverse("votacion:editar_votacion", args=[votacion.pk])
                + "?tab=candidatos#candidatos"
            )
            return HttpResponseRedirect(url_candidatos)

        else:
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
        "pre_candidato": pre_candidato,
        "codigo_pre_candidato": codigo_pre_candidato,
        "candidato_error": candidato_error,
        "tab_activa": tab_activa,
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
    Paso 2 del modo kiosko:
    - Muestra los candidatos activos de la votación.
    - El miembro elige uno.
    - Guardamos el candidato en sesión y vamos a la confirmación.
    """
    votacion, ronda = obtener_votacion_y_ronda_activas()
    miembro_id = request.session.get("kiosko_miembro_id")

    if not votacion or not ronda or not miembro_id:
        # Si falta algo del flujo, volvemos al paso 1
        return redirect("votacion:kiosko_ingreso_codigo")

    miembro = get_object_or_404(Miembro, pk=miembro_id)

    candidatos = (
        votacion.candidatos
        .filter(activo=True)
        .select_related("miembro")
        .order_by("orden", "nombre")
    )

    contexto_base = {
        "votacion": votacion,
        "ronda": ronda,
        "miembro": miembro,
        "candidatos": candidatos,
    }

    if request.method == "POST":
        candidato_id = request.POST.get("candidato_id")

        if not candidato_id:
            contexto = {
                **contexto_base,
                "error": "Debes seleccionar un candidato antes de continuar.",
            }
            return render(
                request,
                "votacion_app/kiosko_seleccion_candidato.html",
                contexto,
            )

        candidato = get_object_or_404(
            Candidato,
            pk=candidato_id,
            votacion=votacion,
            activo=True,
        )

        request.session["kiosko_candidato_id"] = candidato.id
        return redirect("votacion:kiosko_confirmacion")

    # GET: mostrar lista de candidatos
    return render(
        request,
        "votacion_app/kiosko_seleccion_candidato.html",
        contexto_base,
    )



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


def obtener_votacion_y_ronda_activas():
    """
    Devuelve (votacion_activa, ronda_activa) o (None, None) si no hay nada abierto.
    - Toma la última votación en estado ABIERTA.
    - Dentro de esa votación, toma la primera ronda en estado ABIERTA.
    """
    votacion = (
        Votacion.objects
        .filter(estado="ABIERTA")
        .order_by("-creada_el")
        .first()
    )
    if not votacion:
        return None, None

    ronda = (
        votacion.rondas
        .filter(estado="ABIERTA")
        .order_by("numero")
        .first()
    )

    if not ronda:
        # Si quieres obligar a que haya ronda abierta, devolvemos None
        return None, None

    return votacion, ronda

@login_required
def kiosko_ingreso_codigo(request):
    """
    Paso 1 del modo kiosko:
    - El miembro escribe su código (solo número o TF-0000).
    - Validamos:
        * Que haya votación y ronda abiertas.
        * Que el miembro exista.
        * Que esté ACTIVO.
        * Que no haya votado ya en esta vuelta.
    - Guardamos el miembro en sesión y pasamos al Paso 2.
    """
    votacion, ronda = obtener_votacion_y_ronda_activas()

    if not votacion or not ronda:
        return render(
            request,
            "votacion_app/kiosko_ingreso_codigo.html",
            {
                "error": "No hay una votación activa en este momento.",
                "votacion": None,
                "ronda": None,
            },
        )

    contexto_base = {
        "votacion": votacion,
        "ronda": ronda,
    }

    if request.method == "POST":
        codigo = request.POST.get("codigo_miembro", "").strip().upper()

        if not codigo:
            contexto = {
                **contexto_base,
                "error": "Debes introducir tu código de miembro.",
            }
            return render(
                request,
                "votacion_app/kiosko_ingreso_codigo.html",
                contexto,
            )

        # Normalizar código TF-0000
        if not codigo.startswith("TF-"):
            codigo = f"TF-{codigo.zfill(4)}"

        # Buscar miembro
        try:
            miembro = Miembro.objects.get(codigo_miembro__iexact=codigo)
        except Miembro.DoesNotExist:
            contexto = {
                **contexto_base,
                "error": f"El código {codigo} no existe.",
            }
            return render(
                request,
                "votacion_app/kiosko_ingreso_codigo.html",
                contexto,
            )

        # 1) Validar estado
        if miembro.estado_miembro != "activo":
            contexto = {
                **contexto_base,
                "error": "Este miembro no está ACTIVO, no puede votar.",
            }
            return render(
                request,
                "votacion_app/kiosko_ingreso_codigo.html",
                contexto,
            )

        # 2) Validar si ya votó en esta ronda
        if Voto.objects.filter(ronda=ronda, miembro=miembro).exists():
            contexto = {
                **contexto_base,
                "error": "Este miembro ya tiene un voto registrado en esta vuelta.",
            }
            return render(
                request,
                "votacion_app/kiosko_ingreso_codigo.html",
                contexto,
            )

        # OK → Guardamos miembro en sesión y pasamos al paso 2
        request.session["kiosko_miembro_id"] = miembro.id
        return redirect("votacion:kiosko_seleccion_candidato")

    # GET: solo mostramos pantalla
    return render(
        request,
        "votacion_app/kiosko_ingreso_codigo.html",
        contexto_base,
    )
@login_required
def kiosko_confirmacion(request):
    """
    Paso 3 del modo kiosko:
    - Muestra resumen: votación, vuelta, miembro, candidato.
    - Si 'accion' = cambiar -> vuelve a selección de candidato.
    - Si 'accion' = confirmar -> registra el voto y vuelve al paso 1.
    """
    votacion, ronda = obtener_votacion_y_ronda_activas()
    miembro_id = request.session.get("kiosko_miembro_id")
    candidato_id = request.session.get("kiosko_candidato_id")

    if not votacion or not ronda or not miembro_id or not candidato_id:
        # Algo se perdió en el flujo → volvemos al inicio del kiosko
        return redirect("votacion:kiosko_ingreso_codigo")

    miembro = get_object_or_404(Miembro, pk=miembro_id)
    candidato = get_object_or_404(Candidato, pk=candidato_id, votacion=votacion)

    if request.method == "POST":
        accion = request.POST.get("accion")

        # 👉 Botón "Cambiar candidato"
        if accion == "cambiar":
            # Quitamos solo el candidato de la sesión y volvemos al paso 2
            request.session.pop("kiosko_candidato_id", None)
            return redirect("votacion:kiosko_seleccion_candidato")

        # 👉 Botón "Confirmar voto"
        if accion == "confirmar":
            # Seguridad extra: evitar doble voto
            if Voto.objects.filter(ronda=ronda, miembro=miembro).exists():
                messages.error(request, "Este miembro ya tiene un voto registrado en esta vuelta.")
            else:
                try:
                    Voto.objects.create(
                        votacion=votacion,
                        ronda=ronda,
                        miembro=miembro,
                        candidato=candidato,
                        tablet_id=request.META.get("REMOTE_ADDR", "")[:50],
                    )
                    messages.success(request, "Voto registrado correctamente.")
                except IntegrityError:
                    messages.error(request, "Este miembro ya tiene un voto registrado.")

            # Limpiamos todo el flujo del kiosko y volvemos al paso 1
            request.session.pop("kiosko_miembro_id", None)
            request.session.pop("kiosko_candidato_id", None)
            return redirect("votacion:kiosko_ingreso_codigo")

    # GET: mostrar confirmación
    contexto = {
        "votacion": votacion,
        "ronda": ronda,
        "miembro": miembro,
        "candidato": candidato,
    }
    return render(request, "votacion_app/kiosko_confirmacion.html", contexto)

@login_required
def documentacion_sistemas_votacion(request):
    return render(request, "votacion_app/documentacion_sistemas_votacion.html")

