from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q, Max, Count
from django.urls import reverse
from django.http import HttpResponseRedirect
import math
from django.utils import timezone
from django.http import JsonResponse

from miembros_app.models import Miembro
from .models import Votacion, Ronda, Candidato, Voto,  ListaCandidatos, ListaCandidatosItem
from .forms import VotacionForm
from datetime import date
from core.utils_config import get_edad_minima_miembro_oficial   
from .forms import (
    VotacionForm,
    ListaCandidatosForm,
    ListaCandidatosAgregarMiembroForm,
)

def calcular_votos_minimos(votacion):
    """
    Calcula y rellena votacion.votos_minimos_requeridos según:
    - votacion.base_quorum (HABILITADOS / PRESENTES)
    - votacion.tipo_quorum (PORCENTAJE / CANTIDAD)
    - votacion.valor_quorum
    - votacion.total_habilitados / votacion.miembros_presentes
    """
    if votacion.tipo_quorum not in ("PORCENTAJE", "CANTIDAD"):
        votacion.votos_minimos_requeridos = None
        return

    # Base de cálculo
    if votacion.base_quorum == "HABILITADOS":
        base = votacion.total_habilitados
    else:
        base = votacion.miembros_presentes

    if not base or not votacion.valor_quorum:
        votacion.votos_minimos_requeridos = None
        return

    if votacion.tipo_quorum == "PORCENTAJE":
        votacion.votos_minimos_requeridos = math.ceil(
            base * votacion.valor_quorum / 100
        )
    else:
        # CANTIDAD fija
        votacion.votos_minimos_requeridos = votacion.valor_quorum


def calcular_total_miembros_habilitados():
    """
    Devuelve la cantidad de miembros con derecho a voto base:
    - siguen activos en el sistema (activo=True)
    - estado_miembro ACTIVO o PASIVO
    - y cumplen la edad mínima establecida en el sistema de membresía.
    """
    edad_minima = get_edad_minima_miembro_oficial()

    # Tomamos solo los miembros activos en el sistema,
    # con estado_miembro activo/pasivo y con fecha de nacimiento.
    miembros = Miembro.objects.filter(
        activo=True,
        estado_miembro__in=["activo", "pasivo"],
    ).exclude(fecha_nacimiento__isnull=True)

    hoy = date.today()
    total = 0

    for m in miembros:
        fn = m.fecha_nacimiento
        edad = hoy.year - fn.year - (
            (hoy.month, hoy.day) < (fn.month, fn.day)
        )
        if edad >= edad_minima:
            total += 1

    return total




@login_required
def lista_votaciones(request):
    """
    Lista de todas las votaciones.
    Permite cambiar entre vista tipo tabla ("lista")
    y vista en tarjetas ("grid") usando ?vista=lista|grid.
    """
    vista = request.GET.get("vista", "lista")
    if vista not in ("lista", "grid"):
        vista = "lista"

    votaciones = Votacion.objects.all().order_by("-creada_el")

    contexto = {
        "votaciones": votaciones,
        "vista": vista,
    }
    return render(
        request,
        "votacion_app/lista_votaciones.html",
        contexto,
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
            # Guardamos la votación pero forzando el total de habilitados
            votacion = form.save(commit=False)
            votacion.total_habilitados = calcular_total_miembros_habilitados()

            # Calculamos votos mínimos según la base y el tipo de quórum
            calcular_votos_minimos(votacion)

            votacion.save()

            # Crear PRIMERA VUELTA automática
            Ronda.objects.create(
                votacion=votacion,
                numero=1,
                nombre="Primera vuelta",
                estado=votacion.estado,  # normalmente BORRADOR
                fecha_inicio=votacion.fecha_inicio,
                fecha_fin=votacion.fecha_fin,
            )

            messages.success(
                request,
                "La votación se ha creado correctamente con su primera vuelta.",
            )
            return redirect("votacion:editar_votacion", pk=votacion.pk)
    else:
        form = VotacionForm()
        # Inicializamos el campo con el total calculado
        if "total_habilitados" in form.fields:
            form.fields["total_habilitados"].initial = (
                calcular_total_miembros_habilitados()
            )

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
                votacion = form.save(commit=False)

                # Recalcular votos mínimos con los nuevos datos de quórum
                calcular_votos_minimos(votacion)

                votacion.save()

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

            # 👉 AQUÍ ESTÁ EL CAMBIO IMPORTANTE:
            # volvemos a la misma pantalla, pero con la pestaña de candidatos activa
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
    votacion_original = get_object_or_404(Votacion, pk=pk)

    if request.method == "POST":
        try:
            nueva_votacion = Votacion.objects.create(
                nombre=f"{votacion_original.nombre} (copia)",
                descripcion=votacion_original.descripcion,
                tipo=votacion_original.tipo,
                estado="BORRADOR",
                total_habilitados=votacion_original.total_habilitados,
                miembros_presentes=None,  # se contará de nuevo en el día
                base_quorum=votacion_original.base_quorum,
                tipo_quorum=votacion_original.tipo_quorum,
                valor_quorum=votacion_original.valor_quorum,
                votos_minimos_requeridos=votacion_original.votos_minimos_requeridos,
                regla_ganador=votacion_original.regla_ganador,
                numero_cargos=votacion_original.numero_cargos,
                edad_minima_candidato=votacion_original.edad_minima_candidato,
                fecha_inicio=votacion_original.fecha_inicio,
                fecha_fin=votacion_original.fecha_fin,
                permite_empates=votacion_original.permite_empates,
                permite_voto_remoto=votacion_original.permite_voto_remoto,
                observaciones_internas=votacion_original.observaciones_internas,
            )
        except IntegrityError:
            messages.error(
                request,
                "Ocurrió un error al duplicar la votación. Inténtalo de nuevo.",
            )
            return redirect("votacion:editar_votacion", pk=pk)

        # Primera vuelta de la nueva votación
        Ronda.objects.create(
            votacion=nueva_votacion,
            numero=1,
            nombre="Primera vuelta",
            estado=nueva_votacion.estado,
            fecha_inicio=nueva_votacion.fecha_inicio,
            fecha_fin=nueva_votacion.fecha_fin,
        )

        messages.success(
            request,
            "Se ha creado una copia de la votación. Revisa los datos antes de abrirla.",
        )
        return redirect("votacion:editar_votacion", pk=nueva_votacion.pk)

    return redirect("votacion:editar_votacion", pk=pk)



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
    - El miembro escribe su código (4 dígitos).
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
        codigo_raw = request.POST.get("codigo_miembro", "").strip().upper()

        if not codigo_raw:
            contexto = {
                **contexto_base,
                "error": "Debes introducir tu código de miembro.",
            }
            return render(
                request,
                "votacion_app/kiosko_ingreso_codigo.html",
                contexto,
            )

        # Tomamos SOLO los dígitos del código
        # (por si alguien pone TF-0001 desde otro dispositivo)
        solo_digitos = "".join(ch for ch in codigo_raw if ch.isdigit())

        # 🔒 Seguridad: exigir EXACTAMENTE 4 dígitos (0001, 0123, etc.)
        if len(solo_digitos) != 4:
            contexto = {
                **contexto_base,
                "error": "Debes escribir tu código completo de 4 dígitos. Ejemplo: 0001.",
            }
            return render(
                request,
                "votacion_app/kiosko_ingreso_codigo.html",
                contexto,
            )

        # Construimos el código completo TF-0000 sin rellenar con zfill
        codigo_normalizado = f"TF-{solo_digitos}"

        # Buscar miembro
        try:
            miembro = Miembro.objects.get(codigo_miembro__iexact=codigo_normalizado)
        except Miembro.DoesNotExist:
            contexto = {
                **contexto_base,
                "error": f"El código {codigo_normalizado} no existe.",
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
        return redirect("votacion:kiosko_confirmacion_identidad")


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
    - Si 'accion' = confirmar -> registra el voto y pasa a pantalla de voto exitoso.
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

            # Limpiamos todo el flujo del kiosko
            request.session.pop("kiosko_miembro_id", None)
            request.session.pop("kiosko_candidato_id", None)

            # 👉 Ahora vamos a la pantalla de "voto exitoso"
            return redirect("votacion:kiosko_voto_exitoso")

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

@login_required
def kiosko_confirmacion_identidad(request):
    """
    Paso intermedio: mostrar el nombre del miembro y pedir confirmación.
    """
    votacion, ronda = obtener_votacion_y_ronda_activas()

    miembro_id = request.session.get("kiosko_miembro_id")
    if not votacion or not ronda or not miembro_id:
        return redirect("votacion:kiosko_ingreso_codigo")

    miembro = Miembro.objects.filter(id=miembro_id).first()
    if not miembro:
        return redirect("votacion:kiosko_ingreso_codigo")

    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "si":
            # Ir al paso de seleccionar candidatos
            return redirect("votacion:kiosko_seleccion_candidato")

        if accion == "no":
            # Borrar sesión y volver a pedir código
            request.session.pop("kiosko_miembro_id", None)
            return redirect("votacion:kiosko_ingreso_codigo")

    return render(
        request,
        "votacion_app/kiosko_confirmacion_identidad.html",
        {
            "votacion": votacion,
            "ronda": ronda,
            "miembro": miembro,
        }
    )
@login_required
def kiosko_voto_exitoso(request):
    """
    Pantalla final del modo kiosko:
    - Muestra un mensaje de confirmación de voto registrado.
    - Después el usuario puede volver al inicio del kiosko.
    """
    votacion, ronda = obtener_votacion_y_ronda_activas()

    contexto = {
        "votacion": votacion,
        "ronda": ronda,
    }
    return render(request, "votacion_app/kiosko_voto_exitoso.html", contexto)

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max, Count
# ... (lo demás lo dejas como está)


def pantalla_votacion_actual(request):
    """
    Pantalla pública para proyectar la votación.

    - Si hay votación y ronda ABIERTAS:
        modo = "proceso"  → se muestran TODOS los candidatos.
        Si votacion.mostrar_conteo_en_vivo == True (si lo tienes añadido),
        se muestran también los votos en vivo.

    - Si la votación o la ronda están CERRADAS:
        modo = "resultados" → se muestran TODOS los candidatos,
        con sus votos, % y marcados los ganadores.
    """
    # Si ya tienes esta función en otro sitio, reutilízala;
    # aquí asumimos que existe y devuelve (votacion, ronda_activa)
    votacion, ronda = obtener_votacion_y_ronda_activas()

    # Si no hay ninguna votación “activa” para la pantalla
    if not votacion:
        contexto = {
            "votacion": None,
            "ronda": None,
            "modo": "sin_votacion",
            "resultados": [],
            "total_votos": 0,
        }
        return render(request, "votacion_app/pantalla_votacion.html", contexto)

    # ==============================
    # 1) Candidatos de esta votación
    # ==============================
    candidatos_qs = (
        votacion.candidatos
        .filter(activo=True)
        .select_related("miembro")
        .order_by("orden", "nombre")
    )

    # ==============================
    # 2) Votos de esta votación/ronda
    # ==============================
    votos_qs = votacion.votos.all()
    if ronda:
        votos_qs = votos_qs.filter(ronda=ronda)

    conteos = (
        votos_qs
        .values("candidato_id")
        .annotate(total=Count("id"))
    )
    conteos_dict = {row["candidato_id"]: row["total"] for row in conteos}
    total_votos = sum(conteos_dict.values())

    # ==============================
    # 3) Construimos la lista COMPLETA de resultados
    # ==============================
    resultados = []
    for c in candidatos_qs:
        votos = conteos_dict.get(c.id, 0)
        porcentaje = (votos / total_votos * 100) if total_votos > 0 else 0
        resultados.append({
            "candidato": c,
            "votos": votos,
            "porcentaje": porcentaje,
            "es_ganador": False,   # de momento nadie marcado
        })

    # ==============================
    # 4) Modo: proceso vs resultados
    # ==============================
    modo = "proceso"
    if votacion.estado == "CERRADA" or (ronda and ronda.estado == "CERRADA"):
        modo = "resultados"

    # ==============================
    # 5) Marcar ganadores SIN cortar la lista
    # ==============================
    if modo == "resultados" and total_votos > 0:
        # Ordenamos de mayor a menor votos
        resultados.sort(key=lambda x: x["votos"], reverse=True)

        numero_cargos = votacion.numero_cargos or 0

        # 👉 AQUÍ ESTÁ EL PUNTO CLAVE:
        # NO hacemos resultados = resultados[:numero_cargos]
        # Solo marcamos los primeros N como ganadores
        for idx, item in enumerate(resultados):
            if idx < numero_cargos:
                item["es_ganador"] = True

    contexto = {
        "votacion": votacion,
        "ronda": ronda,
        "modo": modo,
        "resultados": resultados,   # lista completa
        "total_votos": total_votos,
    }
    return render(request, "votacion_app/pantalla_votacion.html", contexto)
@login_required
def pantalla_votacion(request, pk):
    """
    Pantalla pública para una votación concreta (la del pk).

    - Si la votación / ronda está ABIERTA:
        modo = "proceso"  → muestra TODOS los candidatos.
        Si tienes el campo 'mostrar_conteo_en_vivo' en el modelo,
        la plantilla decide si muestra o no los votos.

    - Si la votación o la ronda están CERRADAS:
        modo = "resultados" → muestra TODOS los candidatos
        con sus votos, porcentaje y marcados los ganadores.
    """
    votacion = get_object_or_404(Votacion, pk=pk)

    # Buscar la ronda “actual” para esa votación:
    # 1º: una ronda ABIERTA; si no hay, la última por número.
    ronda = (
        votacion.rondas
        .filter(estado="ABIERTA")
        .order_by("numero")
        .first()
    )
    if not ronda:
        ronda = votacion.rondas.order_by("-numero").first()

    # ============================
    # Candidatos de esta votación
    # ============================
    candidatos_qs = (
        votacion.candidatos
        .filter(activo=True)
        .select_related("miembro")
        .order_by("orden", "nombre")
    )

    # ============================
    # Votos de esta votación/ronda
    # ============================
    votos_qs = Voto.objects.filter(votacion=votacion)
    if ronda:
        votos_qs = votos_qs.filter(ronda=ronda)

    conteos = (
        votos_qs
        .values("candidato_id")
        .annotate(total=Count("id"))
    )
    conteos_dict = {row["candidato_id"]: row["total"] for row in conteos}
    total_votos = sum(conteos_dict.values())

    # ============================
    # Construir lista COMPLETA
    # ============================
    resultados = []
    for c in candidatos_qs:
        votos = conteos_dict.get(c.id, 0)
        porcentaje = (votos / total_votos * 100) if total_votos > 0 else 0
        resultados.append({
            "candidato": c,
            "votos": votos,
            "porcentaje": porcentaje,
            "es_ganador": False,  # luego marcamos
        })

    # ============================
    # Determinar modo (proceso / resultados)
    # ============================
    modo = "proceso"
    if votacion.estado == "CERRADA" or (ronda and ronda.estado == "CERRADA"):
        modo = "resultados"

    # ============================
    # Marcar ganadores SIN cortar la lista
    # ============================
    if modo == "resultados" and total_votos > 0:
        # Ordenar de mayor a menor votos
        resultados.sort(key=lambda x: x["votos"], reverse=True)

        numero_cargos = votacion.numero_cargos or 0

        # OJO: NO hacemos resultados = resultados[:numero_cargos]
        # Solo marcamos los primeros N como ganadores
        for idx, item in enumerate(resultados):
            if idx < numero_cargos:
                item["es_ganador"] = True

    contexto = {
        "votacion": votacion,
        "ronda": ronda,
        "modo": modo,
        "resultados": resultados,   # TODOS los candidatos
        "total_votos": total_votos,
    }
    return render(request, "votacion_app/pantalla_votacion.html", contexto)


@login_required
def lista_candidatos_configurar(request, pk=None):
    """
    Crear o editar una lista previa de candidatos.
    - En BORRADOR se pueden añadir y quitar miembros.
    - En CONFIRMADA ya no se puede editar.
    """

    # ============================
    # Cargar lista (si existe)
    # ============================
    if pk:
        lista = get_object_or_404(ListaCandidatos, pk=pk)
    else:
        lista = None

    if lista:
        titulo = f"Editar lista de candidatos: {lista.nombre}"
    else:
        titulo = "Nueva lista de candidatos"

    # Formularios por defecto (GET)
    if lista:
        form = ListaCandidatosForm(instance=lista)
    else:
        # si usas otro helper de código, cámbialo aquí
        form = ListaCandidatosForm(
            initial={"codigo_lista": generar_codigo_lista("LD")}
        )
    agregar_form = ListaCandidatosAgregarMiembroForm()

    # ============================
    # POST: procesar acciones
    # ============================
    if request.method == "POST":
        accion = request.POST.get("accion")

        # 1) Guardar datos básicos de la lista
        if accion in ("guardar", "guardar_seguir"):
            form = ListaCandidatosForm(request.POST, instance=lista)
            if form.is_valid():
                lista = form.save(commit=False)

                # Si es nueva o no tiene código, generamos uno
                if not lista.codigo_lista:
                    lista.codigo_lista = generar_codigo_lista("LD")

                # Estado por defecto
                if not lista.estado:
                    lista.estado = ListaCandidatos.ESTADO_BORRADOR

                lista.save()
                messages.success(
                    request,
                    "La lista de candidatos se ha guardado correctamente.",
                )

                if accion == "guardar_seguir":
                    return redirect(
                        "votacion:lista_candidatos_configurar",
                        pk=lista.pk,
                    )
                return redirect("votacion:lista_candidatos_listado")

        # 2) Agregar miembro (el modal solo confirma en el front)
        elif accion == "agregar_miembro" and lista:
            form = ListaCandidatosForm(instance=lista)
            agregar_form = ListaCandidatosAgregarMiembroForm(request.POST)

            if lista.estado != ListaCandidatos.ESTADO_BORRADOR:
                messages.error(
                    request,
                    "Esta lista ya está confirmada y no se puede modificar.",
                )
                return redirect(
                    "votacion:lista_candidatos_configurar",
                    pk=lista.pk,
                )

            if agregar_form.is_valid():
                sufijo = agregar_form.cleaned_data.get("codigo_sufijo", "").strip()
                if not sufijo:
                    messages.error(
                        request,
                        "Debes introducir el número o el código del miembro.",
                    )
                else:
                    # Normalizar código, ej: TF-0001
                    sufijo_upper = sufijo.upper()
                    if sufijo_upper.startswith("TF-"):
                        codigo_busqueda = sufijo_upper
                    else:
                        limpio = (
                            sufijo_upper.replace("TF", "")
                            .replace("-", "")
                            .strip()
                        )
                        limpio = limpio.zfill(4)
                        codigo_busqueda = f"TF-{limpio}"

                    miembro = Miembro.objects.filter(
                        codigo_miembro__iexact=codigo_busqueda
                    ).first()

                    if not miembro:
                        messages.error(
                            request,
                            f"No se encontró ningún miembro con el código {codigo_busqueda}.",
                        )
                    else:
                        # -------- VALIDACIONES ----------
                        # Estado ACTIVO o PASIVO
                        if miembro.estado_miembro not in ("activo", "pasivo"):
                            messages.error(
                                request,
                                "Solo se pueden añadir a la lista miembros con estado ACTIVO o PASIVO.",
                            )
                        else:
                            # Edad mínima
                            edad_minima = get_edad_minima_miembro_oficial()
                            fn = getattr(miembro, "fecha_nacimiento", None)
                            edad = None
                            if fn:
                                hoy = date.today()
                                edad = hoy.year - fn.year - (
                                    (hoy.month, hoy.day) < (fn.month, fn.day)
                                )

                            if edad is None:
                                messages.error(
                                    request,
                                    "Este miembro no tiene registrada la fecha de nacimiento. "
                                    "Actualiza sus datos antes de añadirlo a la lista.",
                                )
                            elif edad < edad_minima:
                                messages.error(
                                    request,
                                    f"Este miembro no puede incluirse en la lista porque aún "
                                    f"no alcanza la edad mínima de {edad_minima} años.",
                                )
                            else:
                                # Duplicados
                                ya_existe = ListaCandidatosItem.objects.filter(
                                    lista=lista,
                                    miembro=miembro,
                                ).exists()
                                if ya_existe:
                                    messages.warning(
                                        request,
                                        f"El miembro {miembro} ya está en esta lista.",
                                    )
                                else:
                                    # ✅ AQUÍ SÍ SE AGREGA
                                    ListaCandidatosItem.objects.create(
                                        lista=lista,
                                        miembro=miembro,
                                    )
                                    messages.success(
                                        request,
                                        f"Se ha añadido a «{miembro}» a la lista.",
                                    )

            # Siempre volvemos a la misma pantalla
            return redirect(
                "votacion:lista_candidatos_configurar",
                pk=lista.pk,
            )

        # 3) Eliminar un miembro de la lista
        elif accion == "eliminar_item" and lista:
            form = ListaCandidatosForm(instance=lista)
            agregar_form = ListaCandidatosAgregarMiembroForm()

            if lista.estado != ListaCandidatos.ESTADO_BORRADOR:
                messages.error(
                    request,
                    "Esta lista ya está confirmada y no se puede modificar.",
                )
                return redirect(
                    "votacion:lista_candidatos_configurar",
                    pk=lista.pk,
                )

            item_id = request.POST.get("item_id")
            if item_id:
                ListaCandidatosItem.objects.filter(
                    pk=item_id,
                    lista=lista,
                ).delete()
                messages.success(
                    request,
                    "Se ha eliminado el miembro de la lista.",
                )
            else:
                messages.error(
                    request,
                    "No se ha podido identificar el elemento a eliminar.",
                )
            return redirect(
                "votacion:lista_candidatos_configurar",
                pk=lista.pk,
            )

        # 4) Confirmar la lista (BORRADOR → CONFIRMADA)
        elif accion == "confirmar_lista" and lista:
            form = ListaCandidatosForm(instance=lista)
            agregar_form = ListaCandidatosAgregarMiembroForm()

            if lista.estado == ListaCandidatos.ESTADO_CONFIRMADA:
                messages.info(
                    request,
                    "Esta lista ya estaba confirmada.",
                )
                return redirect(
                    "votacion:lista_candidatos_configurar",
                    pk=lista.pk,
                )

            if not lista.items.exists():
                messages.error(
                    request,
                    "No puedes confirmar una lista vacía. Añade al menos un miembro.",
                )
            else:
                lista.estado = ListaCandidatos.ESTADO_CONFIRMADA
                lista.fecha_confirmacion = timezone.now()
                lista.save()
                messages.success(
                    request,
                    "La lista ha sido confirmada correctamente.",
                )
            return redirect(
                "votacion:lista_candidatos_configurar",
                pk=lista.pk,
            )

    # ============================
    # Cargar items para la tabla
    # ============================
    if lista:
        items = (
            ListaCandidatosItem.objects.filter(lista=lista)
            .select_related("miembro")
            .order_by("orden", "miembro__apellidos", "miembro__nombres")
        )
    else:
        items = ListaCandidatosItem.objects.none()

    contexto = {
        "titulo": titulo,
        "lista": lista,
        "form": form,
        "agregar_form": agregar_form,
        "items": items,
    }
    return render(
        request,
        "votacion_app/lista_candidatos_configuracion.html",
        contexto,
    )
@login_required
def lista_candidatos_buscar_miembro(request):
    """
    Endpoint AJAX para buscar un miembro por código, validar
    y devolver nombre + código normalizado + id.
    NO agrega nada, solo sirve para el modal.
    """
    codigo = request.GET.get("codigo", "").strip()

    # Si no hay código, devolvemos error (el JS ya también valida esto)
    if not codigo:
        return JsonResponse({
            "ok": False,
            "error": "Debes introducir un código de miembro."
        })

    # Normalizar igual que en lista_candidatos_configurar
    sufijo_upper = codigo.upper()
    if sufijo_upper.startswith("TF-"):
        codigo_busqueda = sufijo_upper
    else:
        limpio = sufijo_upper.replace("TF", "").replace("-", "").strip()
        limpio = limpio.zfill(4)
        codigo_busqueda = f"TF-{limpio}"

    miembro = Miembro.objects.filter(
        codigo_miembro__iexact=codigo_busqueda
    ).first()

    if not miembro:
        return JsonResponse({
            "ok": False,
            "error": f"No se encontró ningún miembro con el código {codigo_busqueda}."
        })

    # Validaciones básicas (las mismas que al agregar)
    if miembro.estado_miembro not in ("activo", "pasivo"):

        return JsonResponse({
            "ok": False,
            "id": miembro.id,
            "nombre": str(miembro),
            "codigo": miembro.codigo_miembro,
            "error": "El miembro no cumple con las condiciones."
        })

    edad_minima = get_edad_minima_miembro_oficial()
    fn = getattr(miembro, "fecha_nacimiento", None)
    edad = None
    if fn:
        hoy = date.today()
        edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))

    if edad is None:
        return JsonResponse({
            "ok": False,
            "error": "El miembro no tiene fecha de nacimiento registrada."
        })

    if edad < edad_minima:
        return JsonResponse({
            "ok": False,
            "error": f"Este miembro aún no alcanza la edad mínima de {edad_minima} años."
        })

    # Si todo está ok devolvemos nombre + código + id
    return JsonResponse({
        "ok": True,
        "id": miembro.id,
        "nombre": str(miembro),
        "codigo": miembro.codigo_miembro,
    })



@login_required
def lista_candidatos_nueva(request):
    """
    Crea automáticamente una nueva lista en BORRADOR
    y redirige directamente a la pantalla de configuración completa,
    evitando el paso intermedio.
    """
    lista = ListaCandidatos.objects.create(
        nombre="Nueva lista de candidatos",
        estado=ListaCandidatos.ESTADO_BORRADOR,
    )
    messages.success(request, "Se ha creado una nueva lista en borrador.")
    return redirect("votacion:lista_candidatos_configurar", pk=lista.pk)
@login_required
def lista_candidatos_listado(request):
    """
    Lista general de las listas de candidatos.
    Muestra nombre, código, cantidad de miembros, estado, etc.
    """
    listas = (
        ListaCandidatos.objects
        .annotate(total_miembros=Count("items"))
        .order_by("-fecha_confirmacion", "-id")
    )

    contexto = {
        "titulo": "Listas de candidatos",
        "listas": listas,
    }
    return render(request, "votacion_app/lista_candidatos_listado.html", contexto)
@login_required
def lista_candidatos_eliminar(request, pk):
    """
    Elimina una lista de candidatos.
    Se usa POST para evitar eliminaciones accidentales.
    """
    lista = get_object_or_404(ListaCandidatos, pk=pk)

    if request.method == "POST":
        nombre = lista.nombre
        lista.delete()
        messages.success(
            request,
            f"La lista «{nombre}» se ha eliminado correctamente.",
        )
        return redirect("votacion:lista_candidatos_listado")

    # Si entra por GET, lo mandamos a la configuración de la lista
    return redirect("votacion:lista_candidatos_configurar", pk=lista.pk)
from django.utils import timezone
from .models import ListaCandidatos

def generar_codigo_lista(prefix="LD"):
    """
    Genera un código automático para la lista de candidatos.
    Formato: PREFIX-YYYY-XX  (ejemplo: LD-2025-01)
    """
    año = timezone.now().year
    prefijo = f"{prefix}-{año}-"

    # Buscar la última lista que empiece con ese prefijo
    ultima_lista = (
        ListaCandidatos.objects
        .filter(codigo_lista__startswith=prefijo)
        .order_by("codigo_lista")
        .last()
    )

    if not ultima_lista or not ultima_lista.codigo_lista:
        siguiente_numero = 1
    else:
        # Intentamos sacar la parte numérica final (XX)
        try:
            parte_final = ultima_lista.codigo_lista.split("-")[-1]
            siguiente_numero = int(parte_final) + 1
        except (ValueError, IndexError):
            # Si algo raro pasa con el código anterior, empezamos en 1
            siguiente_numero = 1

    return f"{prefijo}{siguiente_numero:02d}"
@login_required
def lista_candidatos_cambiar_estado(request, pk):
    """
    Cambia el estado de una lista de candidatos desde el listado.
    De momento solo usamos la acción 'confirmar' (aprobar lista).
    """
    lista = get_object_or_404(ListaCandidatos, pk=pk)

    if request.method != "POST":
        return redirect("votacion:lista_candidatos_listado")

    accion = request.POST.get("accion")

    if accion == "confirmar":
        # No permitir confirmar listas vacías
        if not lista.items.exists():
            messages.error(
                request,
                "No puedes aprobar una lista vacía. Añade al menos un miembro."
            )
        else:
            lista.estado = ListaCandidatos.ESTADO_CONFIRMADA
            if not lista.fecha_confirmacion:
                lista.fecha_confirmacion = timezone.now()
            lista.save()
            messages.success(
                request,
                f"La lista «{lista.nombre}» ha sido aprobada correctamente."
            )

    # Si en el futuro quieres volverla a borrador, aquí podríamos manejar 'borrador'

    return redirect("votacion:lista_candidatos_listado")



@login_required
def reporte_lista_candidatos(request, pk):
    lista = get_object_or_404(ListaCandidatos, pk=pk)

    items = (
        ListaCandidatosItem.objects
        .filter(lista=lista)
        .select_related("miembro")
        .order_by("miembro__apellidos", "miembro__nombres")
    )

    contexto = {
        "lista": lista,
        "items": items,
        "hoy": timezone.now(),
    }

    return render(request, "votacion_app/reportes/reporte_lista_candidatos.html", contexto)

@login_required
def lista_candidatos_duplicar(request, pk):
    """
    Crea una copia en BORRADOR de una lista de candidatos (incluyendo sus miembros)
    y redirige a la pantalla de configuración de la nueva lista.
    """
    lista = get_object_or_404(ListaCandidatos, pk=pk)

    # Solo aceptamos POST para evitar duplicaciones accidentales por GET
    if request.method != "POST":
        return redirect("votacion:lista_candidatos_listado")

    # Generar un nuevo código automático para la copia
    nuevo_codigo = generar_codigo_lista("LD")

    # Crear nueva lista en BORRADOR
    nueva_lista = ListaCandidatos.objects.create(
        nombre=f"{lista.nombre} (copia)",
        codigo_lista=nuevo_codigo,
        notas=lista.notas,
        estado=ListaCandidatos.ESTADO_BORRADOR,
    )

    # Copiar todos los miembros de la lista original
    for item in lista.items.all().order_by("orden", "miembro__apellidos", "miembro__nombres"):
        ListaCandidatosItem.objects.create(
            lista=nueva_lista,
            miembro=item.miembro,
            orden=item.orden,
        )

    messages.success(
        request,
        f"Se ha creado una copia en borrador de la lista «{lista.nombre}». "
        f"Ahora puedes editarla y volver a confirmarla."
    )

    return redirect("votacion:lista_candidatos_configurar", pk=nueva_lista.pk)
