from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Q, Count
from django.contrib import messages
from django.urls import reverse   # necesario para eliminar_familiar
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required 
from django.utils import timezone
from django.db.models.functions import ExtractDay
from django.http import HttpResponse
from django.conf import settings
from .forms import EnviarFichaMiembroEmailForm
from .forms import EnviarFichaMiembroEmailForm
import tempfile
import subprocess   # ← ESTE
from .models import Miembro, MiembroRelacion, RazonSalidaMiembro
from .forms import MiembroForm, MiembroRelacionForm,NuevoCreyenteForm
import platform   # ← ESTE FALTABA
from core.utils_config import get_edad_minima_miembro_oficial
from django.http import HttpResponse
import traceback
from io import BytesIO
from django.template.loader import render_to_string
import shutil       
import os
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from core.utils_chrome import get_chrome_executable
# Configuración de Chrome/Chromium (ruta opcional)
from openpyxl import Workbook
from datetime import date, timedelta, datetime
from openpyxl import Workbook, load_workbook



CHROME_PATH = getattr(settings, "CHROME_PATH", None) or os.environ.get("CHROME_PATH")


# -------------------------------------
# DASHBOARD
# -------------------------------------
def miembros_dashboard(request):
    miembros = Miembro.objects.all()

    # Edad mínima oficial desde parámetros
    edad_minima = get_edad_minima_miembro_oficial()

    # -----------------------------
    # Cálculo de edades
    # -----------------------------
    def calcular_edad(fecha_nacimiento):
        if not fecha_nacimiento:
            return None
        hoy = date.today()
        edad = hoy.year - fecha_nacimiento.year
        if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
            edad -= 1
        return edad

    # -----------------------------
    # Conteo de membresía oficial y base de porcentaje
    # (solo >= edad_minima)
    # -----------------------------
    activos = 0
    pasivos = 0
    descarriados = 0
    observacion = 0
    disciplina = 0
    catecumenos = 0  # no bautizados en edad oficial

    for m in miembros:
        edad = calcular_edad(m.fecha_nacimiento)
        if edad is None or edad < edad_minima:
            # No se considera miembro oficial (niños fuera de la membresía oficial)
            continue

        # Excluir del cálculo de estado pastoral a los nuevos creyentes
        if m.nuevo_creyente:
            continue

        # Si no está bautizado/confirmado, se cuenta como catecúmeno
        if not m.bautizado_confirmado:
            catecumenos += 1
            continue

        # Miembro oficial bautizado: se distribuye por estado
        if m.estado_miembro == "activo":
            activos += 1
        elif m.estado_miembro == "pasivo":
            pasivos += 1
        elif m.estado_miembro == "descarriado":
            descarriados += 1
        elif m.estado_miembro == "observacion":
            observacion += 1
        elif m.estado_miembro == "disciplina":
            disciplina += 1

    # Total de membresía oficial (para referencia general)
    total_oficiales = (
        activos
        + pasivos
        + observacion
        + disciplina
        + catecumenos
        + descarriados
    )

    # Base para los porcentajes del panel:
    # Se excluyen descarriados y miembros en disciplina,
    # para ver qué proporción de la membresía oficial activa está en estados "sanos":
    # activos, pasivos, observación y catecúmenos.
    total_base = activos + pasivos + observacion + catecumenos

    def porcentaje(cantidad, base=None):
        if base is None:
            base = total_base
        if base == 0:
            return 0
        # 1 decimal para que se vea más fino en las tarjetas
        return round((cantidad * 100) / base, 1)

    # -----------------------------
    # Totales generales y distribución por etapa de vida
    # -----------------------------
    total_miembros = miembros.count()

    campo_categoria = Miembro._meta.get_field("categoria_edad")
    choices_dict = dict(campo_categoria.flatchoices)

    distribucion_raw = (
        miembros.values("categoria_edad")
        .exclude(categoria_edad="")
        .annotate(cantidad=Count("id"))
        .order_by("categoria_edad")
    )

    distribucion_etapa_vida = [
        {
            "codigo": row["categoria_edad"],
            "nombre": choices_dict.get(row["categoria_edad"], "Sin definir"),
            "cantidad": row["cantidad"],
        }
        for row in distribucion_raw
    ]

    # -----------------------------
    # Próximos cumpleaños (30 días)
    # -----------------------------
    hoy = date.today()
    fin_rango = hoy + timedelta(days=30)

    cumple_qs = miembros.filter(fecha_nacimiento__isnull=False)

    proximos_cumpleanos = []
    for m in cumple_qs:
        fn = m.fecha_nacimiento
        proximo = fn.replace(year=hoy.year)
        # Si ya pasó este año, usamos el año siguiente
        if proximo < hoy:
            proximo = proximo.replace(year=hoy.year + 1)

        if hoy <= proximo <= fin_rango:
            edad_que_cumple = proximo.year - fn.year
            proximos_cumpleanos.append(
                {
                    "nombre": f"{m.nombres} {m.apellidos}",
                    "fecha": proximo,
                    "edad": edad_que_cumple,
                }
            )

    proximos_cumpleanos = sorted(proximos_cumpleanos, key=lambda x: x["fecha"])

    # -----------------------------
    # KPI específicos
    # -----------------------------
    # Nuevos miembros del mes (según fecha de ingreso)
    nuevos_mes = miembros.filter(
        fecha_ingreso_iglesia__year=hoy.year,
        fecha_ingreso_iglesia__month=hoy.month,
    ).count()

    # Nuevos creyentes en los últimos 7 días
    hace_7_dias = timezone.now() - timedelta(days=7)
    nuevos_creyentes_semana = Miembro.objects.filter(
        nuevo_creyente=True,
        fecha_creacion__gte=hace_7_dias,
    ).count()

    # Miembros recientes (por si lo usamos luego)
    try:
        miembros_recientes = miembros.order_by(
            "-fecha_ingreso_iglesia", "-fecha_creacion"
        )[:5]
    except Exception:
        # Por si no existiera fecha_creacion en el modelo
        miembros_recientes = miembros.order_by("-fecha_ingreso_iglesia", "-id")[:5]

    # -----------------------------
    # Alertas de datos incompletos
    # -----------------------------
    sin_contacto = miembros.filter(
        (Q(telefono__isnull=True) | Q(telefono="")),
        (Q(telefono_secundario__isnull=True) | Q(telefono_secundario="")),
        (Q(email__isnull=True) | Q(email="")),
    ).count()

    sin_foto = miembros.filter(
        Q(foto__isnull=True) | Q(foto="")
    ).count()

    sin_fecha_nacimiento = miembros.filter(
        fecha_nacimiento__isnull=True
    ).count()

    # -----------------------------
    # Últimas salidas / traslados
    # -----------------------------
    ultimas_salidas = (
        Miembro.objects.filter(activo=False, fecha_salida__isnull=False)
        .order_by("-fecha_salida", "apellidos", "nombres")[:5]
    )

    # -----------------------------
    # Nuevos creyentes recientes (máx. 5)
    # -----------------------------
    nuevos_creyentes_recientes = (
        Miembro.objects.filter(nuevo_creyente=True)
        .order_by("-fecha_creacion", "-id")[:5]
    )

    context = {
        "titulo_pagina": "Miembros",
        "descripcion_pagina": (
            f"Resumen de la membresía oficial "
            f"(mayores de {edad_minima} años) y distribución general."
        ),
        # KPI
        "total_miembros": total_miembros,
        "total_oficiales": total_oficiales,
        "nuevos_mes": nuevos_mes,
        "nuevos_creyentes_semana": nuevos_creyentes_semana,
        # Tarjetas oficiales
        "activos": activos,
        "pasivos": pasivos,
        "descarriados": descarriados,
        "observacion": observacion,
        "disciplina": disciplina,
        "catecumenos": catecumenos,
        "pct_activos": porcentaje(activos),
        "pct_pasivos": porcentaje(pasivos),
        "pct_descarriados": porcentaje(descarriados),
        "pct_observacion": porcentaje(observacion),
        "pct_catecumenos": porcentaje(catecumenos),
        # Gráfico y listas
        "distribucion_etapa_vida": distribucion_etapa_vida,
        "proximos_cumpleanos": proximos_cumpleanos,
        "miembros_recientes": miembros_recientes,
        # Alertas
        "sin_contacto": sin_contacto,
        "sin_foto": sin_foto,
        "sin_fecha_nacimiento": sin_fecha_nacimiento,
        "ultimas_salidas": ultimas_salidas,
        # Panel nuevos creyentes
        "nuevos_creyentes_recientes": nuevos_creyentes_recientes,
        # Parámetro global para la vista
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
    }
    return render(request, "miembros_app/miembros_dashboard.html", context)

# -------------------------------------
# FUNCIÓN AUXILIAR DE FILTRO DE MIEMBROS
# -------------------------------------

def filtrar_miembros(request, miembros_base):
    """
    Aplica todos los filtros del listado general de miembros.
    Devuelve:
        - miembros (queryset o lista filtrada)
        - filtros_context (diccionario para la plantilla)
    """

    # -----------------------------
    # 1. Leer parámetros del GET
    # -----------------------------
    query = request.GET.get("q", "").strip()

    estado = request.GET.get("estado", "").strip()
    categoria_edad_filtro = request.GET.get("categoria_edad", "").strip()
    genero = request.GET.get("genero", "").strip()

    # En el HTML: bautizado = "" / "1" / "0"
    bautizado = request.GET.get("bautizado", "").strip()

    # Checkboxes (vienen solo si están marcados)
    tiene_contacto = request.GET.get("tiene_contacto", "") == "1"
    mostrar_todos = request.GET.get("mostrar_todos", "") == "1"
    incluir_ninos = request.GET.get("incluir_ninos", "") == "1"

    usar_rango_edad = request.GET.get("usar_rango_edad", "") == "1"
    edad_min_str = request.GET.get("edad_min", "").strip()
    edad_max_str = request.GET.get("edad_max", "").strip()

    edad_min = None
    edad_max = None
    if edad_min_str:
        try:
            edad_min = int(edad_min_str)
        except ValueError:
            edad_min = None
    if edad_max_str:
        try:
            edad_max = int(edad_max_str)
        except ValueError:
            edad_max = None

    hoy = date.today()

    # -----------------------------
    # 2. Base de miembros
    # -----------------------------
    miembros = miembros_base

    # Solo activos por defecto. Si NO marcas "Mostrar todos",
    # se filtra por activo=True
    if not mostrar_todos:
        miembros = miembros.filter(activo=True)

    # -----------------------------
    # 3. Exclusión de niños por defecto
    # (niños = menores de 12 años)
    # -----------------------------
    CORTE_NINOS = 12
    cutoff_ninos = hoy - timedelta(days=CORTE_NINOS * 365)

    # Categorías que consideramos "de niños"
    categorias_nino = ("infante", "nino")

    # Si NO marcamos "incluir_ninos" y tampoco estamos filtrando
    # por una categoría de niños, entonces ocultamos los < 12 años
    if not incluir_ninos and categoria_edad_filtro not in categorias_nino:
        miembros = miembros.filter(
            Q(fecha_nacimiento__lte=cutoff_ninos) | Q(fecha_nacimiento__isnull=True)
        )

    # -----------------------------
    # 4. Búsqueda general
    # -----------------------------
    if query:
        miembros = miembros.filter(
            Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(telefono__icontains=query)
            | Q(email__icontains=query)
            | Q(cedula__icontains=query)
        )

    # -----------------------------
    # 5. Filtros simples
    # -----------------------------
    if estado:
        miembros = miembros.filter(estado_miembro=estado)

    if genero:
        miembros = miembros.filter(genero=genero)

    if categoria_edad_filtro:
        miembros = miembros.filter(categoria_edad=categoria_edad_filtro)

    # Bautismo: en el HTML usas 1/0
    if bautizado == "1":
        # Solo bautizados
        miembros = miembros.filter(bautizado_confirmado=True)
    elif bautizado == "0":
        # No bautizados (o sin dato)
        miembros = miembros.filter(
            Q(bautizado_confirmado=False) | Q(bautizado_confirmado__isnull=True)
        )

    # Solo con contacto
    if tiene_contacto:
        miembros = miembros.filter(
            Q(telefono__isnull=False, telefono__gt="")
            | Q(telefono_secundario__isnull=False, telefono_secundario__gt="")
            | Q(email__isnull=False, email__gt="")
        )

    # Orden base
    miembros = miembros.order_by("nombres", "apellidos")

    # -----------------------------
    # 6. Filtro por rango de edad
    # (solo si el check está marcado)
    # -----------------------------
    if usar_rango_edad and (edad_min is not None or edad_max is not None):
        miembros_filtrados = []

        for m in miembros:
            if not m.fecha_nacimiento:
                # Si no tiene fecha de nacimiento, no se puede filtrar por edad
                continue

            # Usamos el método del modelo si existe
            if hasattr(m, "calcular_edad"):
                edad = m.calcular_edad()
            else:
                fn = m.fecha_nacimiento
                edad = hoy.year - fn.year
                if (hoy.month, hoy.day) < (fn.month, fn.day):
                    edad -= 1

            if edad is None:
                continue

            if edad_min is not None and edad < edad_min:
                continue
            if edad_max is not None and edad > edad_max:
                continue

            miembros_filtrados.append(m)

        # Ahora miembros es una lista, no un queryset
        miembros = miembros_filtrados

    # -----------------------------
    # 7. Choices para los selects
    # -----------------------------
    campo_estado = Miembro._meta.get_field("estado_miembro")
    estados_choices = list(campo_estado.flatchoices)

    campo_categoria = Miembro._meta.get_field("categoria_edad")
    categorias_choices = list(campo_categoria.flatchoices)

    try:
        campo_genero = Miembro._meta.get_field("genero")
        generos_choices = list(campo_genero.flatchoices)
    except Exception:
        generos_choices = []

    # -----------------------------
    # 8. Contexto de filtros
    # -----------------------------
    filtros_context = {
        "query": query,
        "mostrar_todos": mostrar_todos,
        "incluir_ninos": incluir_ninos,
        "estado": estado,
        "categoria_edad_filtro": categoria_edad_filtro,
        "genero_filtro": genero,
        "bautizado": bautizado,
        "tiene_contacto": tiene_contacto,
        "estados_choices": estados_choices,
        "categorias_choices": categorias_choices,
        "generos_choices": generos_choices,
        "usar_rango_edad": usar_rango_edad,
        "edad_min": edad_min_str,
        "edad_max": edad_max_str,
    }

    return miembros, filtros_context


# -------------------------------------
# LISTA DE MIEMBROS
# -------------------------------------

def miembro_lista(request):
    """
    Listado general de miembros (versión normal y versión imprimible).
    Usa la función filtrar_miembros para aplicar todos los filtros.
    IMPORTANTE: excluye a los nuevos creyentes (nuevo_creyente=True).
    """

    # Base: solo miembros que NO son nuevos creyentes
    miembros_base = Miembro.objects.filter(nuevo_creyente=False)

    miembros, filtros_context = filtrar_miembros(request, miembros_base)

    # Edad mínima oficial para mostrar en el texto de la plantilla
    edad_minima = get_edad_minima_miembro_oficial()

    context = {
        "miembros": miembros,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
        "modo_pdf": False,   # 👈 importante para distinguir vista normal de PDF
    }
    # Mezclamos con todos los filtros (para que el formulario recuerde el estado)
    context.update(filtros_context)

    return render(
        request,
        "miembros_app/reportes/listado_miembros.html",
        context,
    )

# -------------------------------------
# NOTIFICACIÓN POR CORREO: NUEVO MIEMBRO
# -------------------------------------
from core.models import ConfiguracionSistema
from core.utils_email import enviar_correo_sistema

def notificar_nuevo_miembro(miembro, request=None):
    """
    Envía un correo al correo oficial configurado cuando se registra un nuevo miembro.
    """

    config = ConfiguracionSistema.load()
    destinatario = config.email_oficial or settings.DEFAULT_FROM_EMAIL

    subject = f"Nuevo miembro: {miembro.nombres} {miembro.apellidos}"

    # Fecha de ingreso (evitar errores)
    if getattr(miembro, "fecha_ingreso_iglesia", None):
        fecha_ingreso = miembro.fecha_ingreso_iglesia.strftime("%d/%m/%Y")
    else:
        fecha_ingreso = "-"

    body_html = f"""
        <p>Hola,</p>

        <p>Se ha registrado un nuevo miembro en el sistema <strong>Soid_Tf_2</strong>:</p>

        <p>
            <strong>Nombre:</strong> {miembro.nombres} {miembro.apellidos}<br>
            <strong>Estado:</strong> {miembro.get_estado_miembro_display() or "Sin estado"}<br>
            <strong>Fecha de ingreso:</strong> {fecha_ingreso}
        </p>

        <p>Puedes consultar más detalles desde el sistema.</p>

        <p style="margin-top:16px;">
            Bendiciones,<br>
            <strong>Soid_Tf_2</strong>
        </p>
    """

    # Construir URL del detalle
    button_url = None
    if request is not None:
        try:
            detalle_url = reverse("miembros_app:editar", args=[miembro.pk])
            button_url = request.build_absolute_uri(detalle_url)
        except:
            button_url = None

    enviar_correo_sistema(
        subject=subject,
        heading="Nuevo miembro registrado",
        subheading="Un nuevo miembro ha sido añadido al sistema.",
        body_html=body_html,
        destinatarios=destinatario,
        button_url=button_url,
        button_text="Ver ficha del miembro" if button_url else None,
        meta_text="Correo generado por Soid_Tf_2 automáticamente.",
    )


# -------------------------------------
# CREAR MIEMBRO
# -------------------------------------

def miembro_crear(request):
    """
    Vista normal para crear un miembro.
    Con la lógica de edad mínima tomando el valor desde los parámetros del sistema.
    """

    edad_minima = get_edad_minima_miembro_oficial()

    if request.method == "POST":
        form = MiembroForm(request.POST, request.FILES)

        if form.is_valid():
            miembro = form.save(commit=False)

            # Calcular edad
            edad = None
            if hasattr(miembro, "calcular_edad"):
                edad = miembro.calcular_edad()
            elif miembro.fecha_nacimiento:
                hoy = date.today()
                fn = miembro.fecha_nacimiento
                edad = hoy.year - fn.year
                if (hoy.month, hoy.day) < (fn.month, fn.day):
                    edad -= 1

            # Lógica de edad mínima
            if edad is not None and edad < edad_minima:
                if miembro.estado_miembro:
                    miembro.estado_miembro = ""
                    messages.info(
                        request,
                        (
                            f"Este registro es menor de {edad_minima} años. "
                            "Se ha guardado sin estado de miembro."
                        ),
                    )

            miembro.save()

            # --- AQUÍ DECIDIMOS SEGÚN EL BOTÓN PULSADO ---
            if "guardar_y_nuevo" in request.POST:
                messages.success(
                    request,
                    "Miembro creado correctamente. Puedes registrar otro."
                )
                # Volvemos al formulario de creación limpio
                return redirect("miembros_app:crear")
            else:
                # Botón 'Guardar' normal
                messages.success(request, "Miembro creado correctamente.")
                return redirect("miembros_app:lista")
        else:
            # Si no es válido, se vuelve a mostrar el formulario con errores
            messages.error(
                request,
                "Hay errores en el formulario. Revisa los campos marcados en rojo."
            )
    else:
        form = MiembroForm()

    context = {
        "form": form,
        "modo": "crear",
        "miembro": None,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
    }

    return render(request, "miembros_app/miembro_form.html", context)

# -------------------------------------
# EDITAR MIEMBRO
# -------------------------------------
class MiembroUpdateView(View):
    def get(self, request, pk):
        miembro = get_object_or_404(Miembro, pk=pk)
        form = MiembroForm(instance=miembro)

        # Siempre tomar la edad mínima desde la configuración
        edad_minima = get_edad_minima_miembro_oficial()

        # Usamos MiembroRelacion directamente para evitar problemas con related_name
        familiares_qs = (
            MiembroRelacion.objects
            .filter(miembro=miembro)
            .select_related("familiar")
        )

        # IDs de familiares ya asignados
        familiares_ids = familiares_qs.values_list("familiar_id", flat=True)

        # Lista filtrada para el combo (no mostrar al propio miembro ni a los familiares ya asignados)
        todos_miembros = (
            Miembro.objects
            .exclude(pk=miembro.pk)
            .exclude(pk__in=familiares_ids)
            .order_by("nombres", "apellidos")
        )

        context = {
            "form": form,
            "miembro": miembro,
            "modo": "editar",
            "todos_miembros": todos_miembros,
            "familiares": familiares_qs,  # para la pestaña Familiares
            "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
        }
        return render(request, "miembros_app/miembro_form.html", context)

    def post(self, request, pk):
        miembro = get_object_or_404(Miembro, pk=pk)

        # Siempre tomamos la edad mínima desde la configuración
        edad_minima = get_edad_minima_miembro_oficial()

        # --- SI VIENE DEL BOTÓN "AGREGAR FAMILIAR" ---
        if "agregar_familiar" in request.POST:
            rel_form = MiembroRelacionForm(request.POST)
            if rel_form.is_valid():
                relacion = rel_form.save(commit=False)
                relacion.miembro = miembro
                relacion.save()
                messages.success(request, "Familiar agregado correctamente.")
            else:
                for field, errs in rel_form.errors.items():
                    for e in errs:
                        messages.error(request, f"{field}: {e}")

            # Volver a la pestaña 'familiares'
            return redirect(f"{request.path}?tab=familiares")

        # --- GUARDADO NORMAL DEL MIEMBRO ---
        form = MiembroForm(request.POST, request.FILES, instance=miembro)

        if form.is_valid():
            miembro_editado = form.save(commit=False)

            # Lógica de edad: si es menor de la edad mínima oficial, se guarda SIN estado de miembro
            edad = None
            if miembro_editado.fecha_nacimiento:
                hoy = date.today()
                fn = miembro_editado.fecha_nacimiento
                edad = hoy.year - fn.year
                if (hoy.month, hoy.day) < (fn.month, fn.day):
                    edad -= 1

            if edad is not None and edad < edad_minima:
                if miembro_editado.estado_miembro:
                    miembro_editado.estado_miembro = ""  # sin estado
                    messages.info(
                        request,
                        (
                            f"Este miembro es menor de {edad_minima} años. "
                            "Se ha guardado sin estado de miembro para no contarlo como miembro oficial."
                        ),
                    )

            miembro_editado.save()
            messages.success(request, "Miembro actualizado correctamente.")
            return redirect("miembros_app:lista")

        # Si hay errores, volvemos a cargar el formulario con la lista filtrada
        familiares_qs = (
            MiembroRelacion.objects
            .filter(miembro=miembro)
            .select_related("familiar")
        )
        familiares_ids = familiares_qs.values_list("familiar_id", flat=True)

        todos_miembros = (
            Miembro.objects
            .exclude(pk=miembro.pk)
            .exclude(pk__in=familiares_ids)
            .order_by("nombres", "apellidos")
        )

        context = {
            "form": form,
            "miembro": miembro,
            "modo": "editar",
            "todos_miembros": todos_miembros,
            "familiares": familiares_qs,
            "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
        }
        return render(request, "miembros_app/miembro_form.html", context)

# -------------------------------------
# DETALLE DEL MIEMBRO
# -------------------------------------
class MiembroDetailView(View):
    def get(self, request, pk):
        miembro = get_object_or_404(Miembro, pk=pk)

        # Traemos todas las relaciones donde participa este miembro
        relaciones_qs = (
            MiembroRelacion.objects
            .filter(Q(miembro=miembro) | Q(familiar=miembro))
            .select_related("miembro", "familiar")
        )

        relaciones_familia = []
        parejas_vistas = set()  # para fusionar relaciones de cónyuges recíprocas

        for rel in relaciones_qs:
            if rel.tipo_relacion == "conyuge":
                # Creamos un identificador único para la pareja, sin importar el orden
                pareja = frozenset({rel.miembro_id, rel.familiar_id})

                # Si ya vimos esta pareja en otra relación "conyuge", no la repetimos
                if pareja in parejas_vistas:
                    continue

                parejas_vistas.add(pareja)
                relaciones_familia.append(rel)
            else:
                # Cualquier otra relación (padre, madre, hijo, etc.) se agrega tal cual
                relaciones_familia.append(rel)

        edad_minima = get_edad_minima_miembro_oficial()

        context = {
            "miembro": miembro,
            "relaciones_familia": relaciones_familia,
            "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
        }
        return render(request, "miembros_app/miembros_detalle.html", context)


# -------------------------------------
# AGREGAR FAMILIAR (VERSIÓN ANTIGUA)
# -------------------------------------
def agregar_familiar(request, pk):
    miembro = get_object_or_404(Miembro, pk=pk)

    if request.method == "POST":
        form = MiembroRelacionForm(request.POST)
        if form.is_valid():
            relacion = form.save(commit=False)
            relacion.miembro = miembro
            relacion.save()
            messages.success(request, "Familiar agregado correctamente.")
        else:
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, f"{field}: {e}")

    return redirect("miembros_app:editar", pk=miembro.pk)

@login_required
def miembro_enviar_ficha_email(request, pk):
    miembro = get_object_or_404(Miembro, pk=pk)
    config = ConfiguracionSistema.load()

    # Nombre que verá el destinatario en el adjunto
    nombre_adjunto_auto = f"ficha_miembro_{miembro.pk}.pdf"

    # Datos iniciales para el formulario
    destinatario_inicial = (
        miembro.email
        or config.email_oficial
        or settings.DEFAULT_FROM_EMAIL
    )
    asunto_inicial = f"Ficha del miembro: {miembro.nombres} {miembro.apellidos}"
    mensaje_inicial = (
        f"Le enviamos la ficha del miembro {miembro.nombres} {miembro.apellidos} "
        f"de la iglesia {config.nombre_iglesia or 'Torre Fuerte'}."
    )

     # 👇 AQUÍ EL CAMBIO IMPORTANTE: usar 'ficha' como en la plantilla
    ficha_url = request.build_absolute_uri(
        reverse("miembros_app:ficha", args=[miembro.pk])
    )

    if request.method == "POST":
        # Ya no necesitamos request.FILES porque el PDF lo generamos nosotros
        form = EnviarFichaMiembroEmailForm(request.POST)
        if form.is_valid():
            destinatario = form.cleaned_data["destinatario"]
            asunto = form.cleaned_data["asunto"] or asunto_inicial
            mensaje = form.cleaned_data["mensaje"] or mensaje_inicial

            try:
                # 1) Generar el PDF usando Chrome Headless desde la URL real
                pdf_bytes = generar_pdf_desde_url(ficha_url)

                # 2) Cuerpo HTML del correo
                body_html = (
                    f"<p>{mensaje}</p>"
                    "<p style='margin-top:16px;'>"
                    "Bendiciones,<br>"
                    "<strong>Soid_Tf_2</strong>"
                    "</p>"
                )

                # 3) Enviar correo con el helper genérico
                enviar_correo_sistema(
                    subject=asunto,
                    heading="Ficha de miembro",
                    subheading=f"{miembro.nombres} {miembro.apellidos}",
                    body_html=body_html,
                    destinatarios=destinatario,
                    meta_text="Correo enviado desde el sistema Soid_Tf_2.",
                    extra_context={"CFG": config},
                    # Adjuntamos el PDF EN MEMORIA, igual que en el listado
                    adjuntos=[(nombre_adjunto_auto, pdf_bytes)],
                )

                messages.success(
                    request,
                    f"Correo enviado correctamente a {destinatario}."
                )
                return redirect("miembros_app:detalle", pk=miembro.pk)

            except Exception as e:
                messages.error(
                    request,
                    f"No se pudo enviar el correo: {e}"
                )

    else:
        form = EnviarFichaMiembroEmailForm(
            initial={
                "destinatario": destinatario_inicial,
                "asunto": asunto_inicial,
                "mensaje": mensaje_inicial,
            }
        )

    context = {
        "form": form,
        "miembro": miembro,
        "titulo_pagina": "Enviar ficha por correo",
        "descripcion": "Completa los datos para enviar esta ficha por correo electrónico.",
        "objeto_label": f"Miembro: {miembro.nombres} {miembro.apellidos}",
        "url_cancelar": reverse("miembros_app:detalle", args=[miembro.pk]),
        "adjunto_auto_nombre": nombre_adjunto_auto,
    }
    return render(request, "core/enviar_email.html", context)

# -------------------------------------
# ELIMINAR FAMILIAR
# -------------------------------------
def eliminar_familiar(request, relacion_id):
    """
    Elimina una relación familiar (NO borra al miembro, solo la relación)
    y vuelve a la pantalla de edición en la pestaña 'Familiares'.
    Se permite GET para simplificar el botón 'Quitar'.
    """
    relacion = get_object_or_404(MiembroRelacion, pk=relacion_id)
    miembro_pk = relacion.miembro.pk  # para volver al miembro que estamos editando

    # Eliminamos siempre que se llame a la vista
    relacion.delete()
    messages.success(request, "Familiar quitado correctamente.")

    # Volvemos a la pestaña 'familiares' del mismo miembro
    url = reverse("miembros_app:editar", kwargs={"pk": miembro_pk})
    return redirect(f"{url}?tab=familiares")


def miembro_ficha(request, pk):
    """
    Ficha pastoral imprimible para un miembro concreto.
    """
    miembro = get_object_or_404(Miembro, pk=pk)

    # Traer familiares igual que en el detalle
    relaciones_qs = (
        MiembroRelacion.objects
        .filter(Q(miembro=miembro) | Q(familiar=miembro))
        .select_related("miembro", "familiar")
    )

    relaciones_familia = []
    parejas_vistas = set()

    for rel in relaciones_qs:
        if rel.tipo_relacion == "conyuge":
            pareja = frozenset({rel.miembro_id, rel.familiar_id})
            if pareja in parejas_vistas:
                continue
            parejas_vistas.add(pareja)
            relaciones_familia.append(rel)
        else:
            relaciones_familia.append(rel)

    edad_minima = get_edad_minima_miembro_oficial()

    context = {
        "miembro": miembro,
        "relaciones_familia": relaciones_familia,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
    }

    return render(request, "miembros_app/reportes/miembro_ficha.html", context)


# -------------------------------------
# REPORTES - PANTALLA PRINCIPAL
# -------------------------------------
def reportes_miembros(request):
    """
    Pantalla principal de reportes del módulo de miembros.
    Solo muestra enlaces a los distintos reportes disponibles.
    """
    # Podríamos pasar contadores en el futuro; por ahora es estático.
    return render(request, "miembros_app/reportes/reportes_home.html", {})


# -------------------------------------
# REPORTE: LISTADO GENERAL IMPRIMIBLE
# -------------------------------------
def reporte_listado_miembros(request):
    """
    Alias del listado principal para usarlo desde la sección de reportes.
    """
    return miembro_lista(request)


# -------------------------------------
# REPORTE: FICHA PASTORAL DEL MIEMBRO
# (segunda definición simplificada)
# -------------------------------------
def miembro_ficha(request, pk):
    """
    Ficha pastoral imprimible para un miembro concreto.
    """
    miembro = get_object_or_404(Miembro, pk=pk)

    # Traer familiares igual que en el detalle
    relaciones_qs = (
        MiembroRelacion.objects
        .filter(Q(miembro=miembro) | Q(familiar=miembro))
        .select_related("miembro", "familiar")
    )

    relaciones_familia = []
    parejas_vistas = set()

    for rel in relaciones_qs:
        if rel.tipo_relacion == "conyuge":
            pareja = frozenset({rel.miembro_id, rel.familiar_id})
            if pareja in parejas_vistas:
                continue
            parejas_vistas.add(pareja)
            relaciones_familia.append(rel)
        else:
            relaciones_familia.append(rel)

    edad_minima = get_edad_minima_miembro_oficial()

    context = {
        "miembro": miembro,
        "relaciones_familia": relaciones_familia,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
    }

    return render(request, "miembros_app/reportes/miembro_ficha.html", context)


# --------------------------------------------
# REPORTE: MIEMBROS QUE SE FUERON / TRASLADOS
# --------------------------------------------
def reporte_miembros_salida(request):
    """
    Reporte de miembros inactivos con filtros por fecha y razón de salida.
    Usa el campo razon_salida como ForeignKey a RazonSalidaMiembro.
    """

    query = request.GET.get("q", "").strip()
    fecha_desde_str = request.GET.get("fecha_desde", "").strip()
    fecha_hasta_str = request.GET.get("fecha_hasta", "").strip()
    razon_salida_id_str = request.GET.get("razon_salida", "").strip()

    # Base: solo miembros inactivos
    miembros = Miembro.objects.filter(activo=False)

    # Filtro de búsqueda general
    if query:
        miembros = miembros.filter(
            Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(email__icontains=query)
            | Q(telefono__icontains=query)
            | Q(telefono_secundario__icontains=query)
        )

    # Filtros de fecha
    if fecha_desde_str:
        try:
            fecha_desde = date.fromisoformat(fecha_desde_str)
            miembros = miembros.filter(fecha_salida__gte=fecha_desde)
        except ValueError:
            pass

    if fecha_hasta_str:
        try:
            fecha_hasta = date.fromisoformat(fecha_hasta_str)
            miembros = miembros.filter(fecha_salida__lte=fecha_hasta)
        except ValueError:
            pass

    # Filtro por razón de salida (ForeignKey)
    razon_salida_id = None
    razon_salida_obj = None
    if razon_salida_id_str and razon_salida_id_str.isdigit():
        razon_salida_id = int(razon_salida_id_str)
        miembros = miembros.filter(razon_salida_id=razon_salida_id)
        razon_salida_obj = RazonSalidaMiembro.objects.filter(pk=razon_salida_id).first()

    # Razones disponibles (solo activas)
    razones_disponibles = RazonSalidaMiembro.objects.filter(activo=True).order_by(
        "orden", "nombre"
    )

    # Orden final
    miembros = miembros.order_by("-fecha_salida", "apellidos", "nombres")

    context = {
        "miembros": miembros,
        "query": query,
        "fecha_desde": fecha_desde_str,
        "fecha_hasta": fecha_hasta_str,
        "razones_disponibles": razones_disponibles,
        "razon_salida_id": razon_salida_id,
        "razon_salida_obj": razon_salida_obj,
    }

    return render(
        request,
        "miembros_app/reportes/reporte_miembros_salida.html",
        context,
    )


# -------------------------------------
# REPORTE: RELACIONES FAMILIARES
# -------------------------------------
# -------------------------------------
# REPORTE: RELACIONES FAMILIARES
# -------------------------------------
def reporte_relaciones_familiares(request):
    """
    Reporte de relaciones familiares entre miembros.
    Muestra quién está relacionado con quién (cónyuges, hijos, etc.),
    con filtros por tipo de relación, convivencia y responsable.
    """

    # Texto de búsqueda
    query = request.GET.get("q", "").strip()

    # Filtros booleanos
    solo_miembros = request.GET.get("solo_miembros", "") == "1"
    solo_conviven = request.GET.get("solo_conviven", "") == "1"
    solo_responsables = request.GET.get("solo_responsables", "") == "1"

    # Filtro por tipo de relación (padre, madre, hijo, conyuge, etc.)
    tipo_relacion = request.GET.get("tipo_relacion", "").strip()

    # Base queryset
    relaciones = (
        MiembroRelacion.objects
        .select_related("miembro", "familiar")
        .all()
    )

    # Búsqueda por nombres / apellidos de miembro o familiar
    if query:
        relaciones = relaciones.filter(
            Q(miembro__nombres__icontains=query)
            | Q(miembro__apellidos__icontains=query)
            | Q(familiar__nombres__icontains=query)
            | Q(familiar__apellidos__icontains=query)
        )

    # Solo relaciones donde el familiar también es miembro registrado
    # (en tu modelo 'familiar' siempre es un Miembro, pero mantenemos el filtro
    # por si en el futuro se permite null)
    if solo_miembros:
        relaciones = relaciones.filter(familiar__isnull=False)

    # Filtro por tipo de relación
    if tipo_relacion:
        relaciones = relaciones.filter(tipo_relacion=tipo_relacion)

    # Solo los que viven juntos
    if solo_conviven:
        relaciones = relaciones.filter(vive_junto=True)

    # Solo responsables principales
    if solo_responsables:
        relaciones = relaciones.filter(es_responsable=True)

    # Orden: por miembro y tipo de relación
    relaciones = relaciones.order_by(
        "miembro__apellidos",
        "miembro__nombres",
        "tipo_relacion",
    )

    context = {
        "relaciones": relaciones,
        "query": query,
        "solo_miembros": solo_miembros,
        "solo_conviven": solo_conviven,
        "solo_responsables": solo_responsables,
        "tipo_relacion": tipo_relacion,
        "tipo_relacion_choices": MiembroRelacion.TIPO_RELACION_CHOICES,
    }
    return render(
        request,
        "miembros_app/reportes/reporte_relaciones_familiares.html",
        context,
    )

# -------------------------------------
# REPORTE: CUMPLEAÑOS DEL MES
# -------------------------------------
def reporte_cumple_mes(request):
    """
    Reporte imprimible de los cumpleaños de un mes.
    - Por defecto muestra el mes actual.
    - Filtros:
        * solo_activos: solo miembros activos en Torre Fuerte.
        * solo_oficiales: solo mayores de edad mínima oficial.
    """

    hoy = timezone.localdate()
    edad_minima = get_edad_minima_miembro_oficial()

    # --- Mes seleccionado ---
    mes_str = request.GET.get("mes", "").strip()
    if mes_str.isdigit():
        mes = int(mes_str)
        if mes < 1 or mes > 12:
            mes = hoy.month
    else:
        mes = hoy.month

    # Año solo para mostrar en el título (no afecta el filtro)
    anio = hoy.year

    # Flags de filtros (por defecto: solo_activos=ON, solo_oficiales=OFF)
    solo_activos = request.GET.get("solo_activos", "1") == "1"
    solo_oficiales = request.GET.get("solo_oficiales", "0") == "1"

    # Nombres de meses
    MESES_ES = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }
    nombre_mes = MESES_ES.get(mes, "")

    # Base: miembros con fecha de nacimiento en ese mes
    miembros = Miembro.objects.filter(
        fecha_nacimiento__isnull=False,
        fecha_nacimiento__month=mes,
    )

    # Solo activos (siguen en la iglesia)
    if solo_activos:
        miembros = miembros.filter(activo=True)

    # Solo oficiales (>= edad mínima)
    if solo_oficiales:
        cutoff = hoy - timedelta(days=edad_minima * 365)
        miembros = miembros.filter(fecha_nacimiento__lte=cutoff)

    # Añadimos el día del mes y ordenamos
    miembros = (
        miembros
        .annotate(dia=ExtractDay("fecha_nacimiento"))
        .order_by("dia", "apellidos", "nombres")
    )

    # Calculamos cuántos años cumplen (edad_que_cumple)
    for m in miembros:
        if m.fecha_nacimiento:
            edad_actual = m.calcular_edad()
            if edad_actual is not None:
                m.edad_que_cumple = edad_actual + 1
            else:
                m.edad_que_cumple = None
        else:
            m.edad_que_cumple = None

    context = {
        "miembros": miembros,
        "mes": mes,
        "anio": anio,
        "nombre_mes": nombre_mes,
        "solo_activos": solo_activos,
        "solo_oficiales": solo_oficiales,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
    }

    return render(request, "miembros_app/reportes/cumple_mes.html", context)


# -------------------------------------
# REPORTE: MIEMBROS NUEVOS DEL MES
# -------------------------------------
def reporte_miembros_nuevos_mes(request):
    """
    Reporte de miembros que ingresaron a la iglesia en un mes concreto.
    - Por defecto muestra el mes actual.
    - Filtros:
        * solo_activos: solo miembros activos en Torre Fuerte.
        * solo_oficiales: solo mayores de edad mínima oficial.
    """

    hoy = timezone.localdate()
    edad_minima = get_edad_minima_miembro_oficial()

    # --- Mes seleccionado (input type="month" -> YYYY-MM) ---
    mes_str = request.GET.get("mes", "").strip()

    if mes_str:
        # Intentamos parsear "YYYY-MM"
        try:
            partes = mes_str.split("-")
            anio = int(partes[0])
            mes = int(partes[1])
            if mes < 1 or mes > 12:
                raise ValueError
        except Exception:
            anio = hoy.year
            mes = hoy.month
            mes_str = f"{anio:04d}-{mes:02d}"
    else:
        anio = hoy.year
        mes = hoy.month
        mes_str = f"{anio:04d}-{mes:02d}"

    # --- Flags de filtros (por defecto: solo_activos=ON, solo_oficiales=OFF) ---
    solo_activos = request.GET.get("solo_activos", "1") == "1"
    solo_oficiales = request.GET.get("solo_oficiales", "0") == "1"

    # Texto de búsqueda
    query = request.GET.get("q", "").strip()

    # Nombres de meses (para mostrar título bonito)
    MESES_ES = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }
    nombre_mes = MESES_ES.get(mes, "")

    # --- Rango de fechas del mes seleccionado ---
    # Primer día del mes
    fecha_inicio = date(anio, mes, 1)
    # Primer día del mes siguiente
    if mes == 12:
        fecha_fin_mes_siguiente = date(anio + 1, 1, 1)
    else:
        fecha_fin_mes_siguiente = date(anio, mes + 1, 1)
    # Último día del mes seleccionado
    fecha_fin = fecha_fin_mes_siguiente - timedelta(days=1)

    # Base: miembros con fecha de ingreso en ese rango
    miembros = Miembro.objects.filter(
        fecha_ingreso_iglesia__isnull=False,
        fecha_ingreso_iglesia__gte=fecha_inicio,
        fecha_ingreso_iglesia__lte=fecha_fin,
    )

    # Solo activos (siguen en la iglesia)
    if solo_activos:
        miembros = miembros.filter(activo=True)

    # Solo oficiales (>= edad mínima)
    if solo_oficiales:
        cutoff = hoy - timedelta(days=edad_minima * 365)
        miembros = miembros.filter(
            Q(fecha_nacimiento__isnull=False) & Q(fecha_nacimiento__lte=cutoff)
        )

    # Búsqueda por nombre, apellidos, correo o teléfono
    if query:
        miembros = miembros.filter(
            Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(email__icontains=query)
            | Q(telefono__icontains=query)
            | Q(telefono_secundario__icontains=query)
        )

    # Orden: por fecha de ingreso y luego por nombre
    miembros = miembros.order_by(
        "fecha_ingreso_iglesia",
        "apellidos",
        "nombres",
    )

    # Calculamos la edad actual (para mostrar en la tabla)
    for m in miembros:
        if hasattr(m, "calcular_edad"):
            m.edad_actual = m.calcular_edad()
        else:
            if m.fecha_nacimiento:
                fn = m.fecha_nacimiento
                edad = hoy.year - fn.year
                if (hoy.month, hoy.day) < (fn.month, fn.day):
                    edad -= 1
                m.edad_actual = edad
            else:
                m.edad_actual = None

    context = {
        "miembros": miembros,
        "mes_str": mes_str,
        "anio": anio,
        "mes": mes,
        "nombre_mes": nombre_mes,
        "solo_activos": solo_activos,
        "solo_oficiales": solo_oficiales,
        "query": query,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
    }

    return render(
        request,
        "miembros_app/reportes/reporte_miembros_nuevos_mes.html",
        context,
    )


# -------------------------------
# CARTA DE SALIDA / TRASLADO
# -------------------------------
def carta_salida_miembro(request, pk):
    """
    Genera una carta imprimible de salida / traslado para un miembro.
    En caso de error, muestra el mensaje en pantalla para depurar.
    """
    try:
        miembro = get_object_or_404(Miembro, pk=pk)

        hoy = timezone.localdate()

        iglesia_nombre = getattr(settings, "NOMBRE_IGLESIA", "Iglesia Torre Fuerte")
        iglesia_ciudad = getattr(
            settings, "CIUDAD_IGLESIA", "Higüey, República Dominicana"
        )
        pastor_principal = getattr(
            settings, "PASTOR_PRINCIPAL", "Pastor de la iglesia"
        )

        context = {
            "miembro": miembro,
            "hoy": hoy,
            "iglesia_nombre": iglesia_nombre,
            "iglesia_ciudad": iglesia_ciudad,
            "pastor_principal": pastor_principal,
        }

        return render(
            request,
            "miembros_app/cartas/carta_salida.html",
            context,
        )

    except Exception as e:
        import traceback
        # Imprime el error en la consola (por si acaso)
        traceback.print_exc()
        # Y lo muestra en el navegador para que sepamos qué está pasando
        return HttpResponse(
            f"<h2>Error en carta_salida_miembro</h2>"
            f"<pre>{e}</pre>",
            status=500,
        )
from django.utils import timezone  # ya lo tienes arriba
def nuevo_creyente_crear(request):
    """
    Registro rápido de nuevos creyentes.
    Guarda en Miembro pero marcando nuevo_creyente=True
    y sin mezclarlos todavía con la membresía oficial.
    """
    if request.method == "POST":
        form = NuevoCreyenteForm(request.POST)
        if form.is_valid():
            miembro = form.save()
            messages.success(
                request,
                f"Nuevo creyente registrado correctamente: {miembro.nombres} {miembro.apellidos}.",
            )
            return redirect("miembros_app:nuevo_creyente_lista")
    else:
        form = NuevoCreyenteForm()

    context = {
        "form": form,
        "modo": "crear",  # 👈 importante para el template
    }
    return render(request, "miembros_app/nuevos_creyentes_form.html", context)



def nuevo_creyente_lista(request):
    """
    Lista de nuevos creyentes (miembros con nuevo_creyente=True),
    con filtros por texto, género, rango de fecha de conversión
    y si tienen o no datos de contacto.
    """

    query = request.GET.get("q", "").strip()
    genero_filtro = request.GET.get("genero", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()
    solo_contacto = request.GET.get("solo_contacto", "") == "1"

    miembros = Miembro.objects.filter(nuevo_creyente=True)

    # Búsqueda por nombre / contacto
    if query:
        miembros = miembros.filter(
            Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(telefono__icontains=query)
            | Q(telefono_secundario__icontains=query)
            | Q(email__icontains=query)
        )

    # Filtro por género
    if genero_filtro:
        miembros = miembros.filter(genero=genero_filtro)

    # Filtro por rango de fecha de conversión
    if fecha_desde:
        try:
            miembros = miembros.filter(fecha_conversion__gte=fecha_desde)
        except ValueError:
            pass

    if fecha_hasta:
        try:
            miembros = miembros.filter(fecha_conversion__lte=fecha_hasta)
        except ValueError:
            pass

    # Solo los que tienen algún dato de contacto
    if solo_contacto:
        miembros = miembros.filter(
            Q(telefono__isnull=False, telefono__gt="")
            | Q(telefono_secundario__isnull=False, telefono_secundario__gt="")
            | Q(email__isnull=False, email__gt="")
        )

    miembros = miembros.order_by(
        "-fecha_conversion",
        "-fecha_creacion",
        "apellidos",
        "nombres",
    )

    # Para llenar el select de género en la plantilla
    generos_choices = Miembro._meta.get_field("genero").choices

    context = {
        "miembros": miembros,
        "query": query,
        "genero_filtro": genero_filtro,
        "generos_choices": generos_choices,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "solo_contacto": solo_contacto,
        "hoy": timezone.localdate(),
    }
    return render(
        request,
        "miembros_app/nuevos_creyentes_lista.html",
        context,
    )
def nuevo_creyente_editar(request, pk):
    """
    Editar un nuevo creyente usando el mismo formulario sencillo.
    Solo permite editar registros marcados como nuevo_creyente=True.
    """
    miembro = get_object_or_404(Miembro, pk=pk, nuevo_creyente=True)

    if request.method == "POST":
        form = NuevoCreyenteForm(request.POST, instance=miembro)
        if form.is_valid():
            miembro = form.save()
            messages.success(
                request,
                f"Datos del nuevo creyente actualizados: {miembro.nombres} {miembro.apellidos}."
            )
            return redirect("miembros_app:nuevo_creyente_lista")
    else:
        form = NuevoCreyenteForm(instance=miembro)

    context = {
        "form": form,
        "modo": "editar",  # 👈 así el template sabe que está en modo edición
        "miembro": miembro,
    }
    return render(request, "miembros_app/nuevos_creyentes_form.html", context)
# -------------------------------------
# REPORTE: NUEVOS CREYENTES
# -------------------------------------
def reporte_nuevos_creyentes(request):
    """
    Reporte imprimible de nuevos creyentes.
    Permite filtrar por nombre/contacto y por rango de fecha de conversión.
    """
    query = request.GET.get("q", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()
    solo_contacto = request.GET.get("solo_contacto", "") == "1"

    miembros = Miembro.objects.filter(nuevo_creyente=True)

    # --- Búsqueda general ---
    if query:
        miembros = miembros.filter(
            Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(telefono__icontains=query)
            | Q(telefono_secundario__icontains=query)
            | Q(email__icontains=query)
        )

    # --- Filtro por fechas ---
    if fecha_desde:
        try:
            miembros = miembros.filter(fecha_conversion__gte=fecha_desde)
        except:
            pass

    if fecha_hasta:
        try:
            miembros = miembros.filter(fecha_conversion__lte=fecha_hasta)
        except:
            pass

    # --- Solo los que tienen algún contacto ---
    if solo_contacto:
        miembros = miembros.filter(
            Q(telefono__isnull=False, telefono__gt="")
            | Q(telefono_secundario__isnull=False, telefono_secundario__gt="")
            | Q(email__isnull=False, email__gt="")
        )

    miembros = miembros.order_by(
        "-fecha_conversion",
        "-fecha_creacion",
        "apellidos",
        "nombres",
    )

    context = {
        "miembros": miembros,
        "query": query,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "solo_contacto": solo_contacto,
        "hoy": timezone.localdate(),
    }

    return render(
        request,
        "miembros_app/reportes/reporte_nuevos_creyentes.html",
        context,
    )
def nuevo_creyente_ficha(request, pk):
    """
    Ficha imprimible del nuevo creyente.
    """
    miembro = get_object_or_404(Miembro, pk=pk, nuevo_creyente=True)

    context = {
        "miembro": miembro,
        "hoy": timezone.localdate(),
    }
    return render(
        request,
        "miembros_app/reportes/nuevo_creyente_ficha.html",
        context,
    )
def generar_pdf_ficha_miembro(miembro):
    """
    Genera un PDF de la ficha pastoral del miembro y devuelve
    la ruta absoluta del archivo generado.
    """
    from django.conf import settings

    # Configuración general (para CFG en la plantilla)
    config = ConfiguracionSistema.load()

    # Traer familiares igual que en la ficha imprimible
    relaciones_qs = (
        MiembroRelacion.objects
        .filter(Q(miembro=miembro) | Q(familiar=miembro))
        .select_related("miembro", "familiar")
    )

    relaciones_familia = []
    parejas_vistas = set()

    for rel in relaciones_qs:
        if rel.tipo_relacion == "conyuge":
            pareja = frozenset({rel.miembro_id, rel.familiar_id})
            if pareja in parejas_vistas:
                continue
            parejas_vistas.add(pareja)
            relaciones_familia.append(rel)
        else:
            relaciones_familia.append(rel)

    edad_minima = get_edad_minima_miembro_oficial()

    # ✨ AQUÍ SÍ INCLUIMOS CFG EN EL CONTEXTO
    context = {
        "miembro": miembro,
        "relaciones_familia": relaciones_familia,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
        "CFG": config,  # ← ESTA ES LA CLAVE QUE FALTABA
    }

    # Renderizamos la misma plantilla que usas para imprimir la ficha
    html = render_to_string("miembros_app/reportes/miembro_ficha.html", context)

    # Creamos el PDF en memoria
    resultado = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=resultado)

    if pisa_status.err:
        raise Exception("Error generando el PDF de la ficha del miembro.")

    # Carpeta donde guardaremos las fichas
    carpeta = os.path.join(settings.MEDIA_ROOT, "fichas_miembro")
    os.makedirs(carpeta, exist_ok=True)

    nombre_archivo = f"ficha_miembro_{miembro.pk}.pdf"
    ruta_pdf = os.path.join(carpeta, nombre_archivo)

    # Guardamos el contenido del PDF en disco
    with open(ruta_pdf, "wb") as f:
        f.write(resultado.getvalue())

    return ruta_pdf
@login_required
def listado_miembros_enviar_email(request):
    """
    Genera un PDF EXACTO del listado de miembros usando la URL real
    y lo envía por correo.
    """
    config = ConfiguracionSistema.load()

    # Obtener los filtros actuales
    filtros = request.GET.urlencode()
    base_url = request.build_absolute_uri(reverse("miembros_app:reporte_listado_miembros"))

    # Construir URL completa con filtros
    url_completa = base_url + (f"?{filtros}" if filtros else "")

    # Datos iniciales del formulario
    email_default = config.email_oficial or settings.DEFAULT_FROM_EMAIL
    asunto_default = "Listado general de miembros"
    mensaje_default = f"Adjunto el listado general de miembros de {config.nombre_iglesia or 'nuestra iglesia'}."

    if request.method == "POST":
        form = EnviarFichaMiembroEmailForm(request.POST)
        if form.is_valid():
            destinatario = form.cleaned_data["destinatario"]
            asunto = form.cleaned_data["asunto"] or asunto_default
            mensaje = form.cleaned_data["mensaje"] or mensaje_default

            try:
                # GENERAR PDF USANDO LA URL REAL
                pdf_bytes = generar_pdf_desde_url(url_completa)

                # Cuerpo del correo
                body_html = (
                    f"<p>{mensaje}</p>"
                    "<p style='margin-top:16px;'>Bendiciones,<br><strong>Soid_Tf_2</strong></p>"
                )

                # Enviar correo con adjunto
                enviar_correo_sistema(
                    subject=asunto,
                    heading="Listado general de miembros",
                    body_html=body_html,
                    destinatarios=destinatario,
                    meta_text="Correo enviado desde Soid_Tf_2",
                    extra_context={"CFG": config},
                    adjuntos=[("listado_miembros.pdf", pdf_bytes)],
                )

                messages.success(
                    request, f"Correo enviado correctamente a {destinatario}"
                )
                return redirect("miembros_app:reporte_listado_miembros")

            except Exception as e:
                messages.error(request, f"No se pudo enviar el correo: {e}")
                return redirect("miembros_app:reporte_listado_miembros")

    else:
        form = EnviarFichaMiembroEmailForm(
            initial={
                "destinatario": email_default,
                "asunto": asunto_default,
                "mensaje": mensaje_default,
            }
        )

    return render(
        request,
        "core/enviar_email.html",
        {
            "form": form,
            "titulo_pagina": "Enviar listado por correo",
            "descripcion": "Se generará un PDF idéntico al de impresión usando Chrome Headless.",
            "objeto_label": "Listado general de miembros",
            "url_cancelar": reverse("miembros_app:reporte_listado_miembros"),
            "adjunto_auto_nombre": "listado_miembros.pdf",
        },
    )




def generar_pdf_listado_miembros(request, miembros, filtros_context):
    """
    Genera un PDF usando la MISMA plantilla del listado,
    conservando el diseño original sin modificar nada.
    """
    config = ConfiguracionSistema.load()
    edad_minima = get_edad_minima_miembro_oficial()

    # Contexto igualito al de la vista original
    context = {
        "miembros": miembros,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
        "CFG": config,
        "hoy": timezone.localdate(),
    }
    context.update(filtros_context)

    # Renderizamos el MISMO HTML del listado
    html_string = render_to_string(
        "miembros_app/reportes/listado_miembros.html",
        context
    )

    # Convertir el HTML a PDF
    pdf_file = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file)

    # Guardar en MEDIA/reportes_miembros/
    carpeta = os.path.join(settings.MEDIA_ROOT, "reportes_miembros")
    os.makedirs(carpeta, exist_ok=True)

    ruta_pdf = os.path.join(carpeta, "listado_miembros.pdf")

    with open(ruta_pdf, "wb") as f:
        f.write(pdf_file.getvalue())

    return ruta_pdf
def generar_pdf_chrome_headless(request, html_content):
    """
    Genera un PDF en memoria usando Chrome Headless.
    El resultado es idéntico al PDF que genera el navegador.
    """
    chrome_path = get_chrome_path()

    # Crear archivo HTML temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as html_temp:
        html_temp.write(html_content.encode("utf-8"))
        html_temp_path = html_temp.name

    # Archivo PDF temporal (salida)
    pdf_temp_path = html_temp_path.replace(".html", ".pdf")

    comando = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={pdf_temp_path}",
        html_temp_path,
    ]

    resultado = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            f"Error ejecutando Chrome Headless (código {resultado.returncode}): {resultado.stderr}"
        )

    with open(pdf_temp_path, "rb") as f:
        pdf_bytes = f.read()

    os.remove(html_temp_path)
    os.remove(pdf_temp_path)

    return pdf_bytes
def generar_pdf_desde_url(url):
    """
    Genera un PDF desde una URL real usando Chrome Headless.
    El PDF es idéntico al generado desde 'Imprimir → Guardar como PDF'.
    """
    chrome_path = get_chrome_path()

    # Crear archivo PDF temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as pdf_temp:
        pdf_temp_path = pdf_temp.name

    comando = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={pdf_temp_path}",
        url,  # aquí va la URL, no html_temp_path
    ]

    resultado = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            f"Error ejecutando Chrome Headless (código {resultado.returncode}): {resultado.stderr}"
        )

    with open(pdf_temp_path, "rb") as f:
        pdf_bytes = f.read()

    os.remove(pdf_temp_path)

    return pdf_bytes


def get_chrome_path():
    """
    Devuelve una ruta válida al ejecutable de Chrome/Chromium.
    Orden de prioridad:
    1) settings.CHROME_PATH
    2) variable de entorno CHROME_PATH
    3) detección automática (rutas típicas y ejecutables conocidos)
    """
    global CHROME_PATH

    # 1) Si ya está resuelto y existe, úsalo
    if CHROME_PATH and os.path.exists(CHROME_PATH):
        return CHROME_PATH

    # 2) Revisar settings.CHROME_PATH
    settings_path = getattr(settings, "CHROME_PATH", "") or ""
    if settings_path and os.path.exists(settings_path):
        CHROME_PATH = settings_path
        return CHROME_PATH

    # 3) Revisar variable de entorno CHROME_PATH
    env_path = os.environ.get("CHROME_PATH")
    if env_path and os.path.exists(env_path):
        CHROME_PATH = env_path
        return CHROME_PATH

    # 4) Detección automática según sistema operativo
    system = platform.system()

    candidatos = []
    if system == "Windows":
        candidatos = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            shutil.which("chrome"),
            shutil.which("msedge"),  # Edge (Chromium) también sirve
        ]
    else:
        candidatos = [
            shutil.which("google-chrome"),
            shutil.which("google-chrome-stable"),
            shutil.which("chromium"),
            shutil.which("chromium-browser"),
        ]

    for ruta in candidatos:
        if ruta and os.path.exists(ruta):
            CHROME_PATH = ruta
            return CHROME_PATH

    # 5) Si no se encuentra nada, error real
    raise RuntimeError(
        "No se encontró Chrome/Chromium. "
        "Instálalo o define CHROME_PATH en settings.py o en variables de entorno."
    )
@login_required
def nuevos_creyentes_enviar_email(request):
    """
    Genera un PDF del listado de nuevos creyentes (con los filtros actuales)
    y lo envía por correo.
    """
    config = ConfiguracionSistema.load()

    # Tomamos los filtros que estén activos en la URL
    filtros = request.GET.urlencode()

    # OJO: el name correcto de la ruta es 'nuevo_creyente_lista'
    base_url = request.build_absolute_uri(
        reverse("miembros_app:nuevo_creyente_lista")
    )
    url_completa = base_url + (f"?{filtros}" if filtros else "")

    email_default = config.email_oficial or settings.DEFAULT_FROM_EMAIL
    asunto_default = "Listado de nuevos creyentes"
    mensaje_default = (
        f"Adjunto el listado de nuevos creyentes de "
        f"{config.nombre_iglesia or 'nuestra iglesia'}."
    )

    if request.method == "POST":
        form = EnviarFichaMiembroEmailForm(request.POST)
        if form.is_valid():
            destinatario = form.cleaned_data["destinatario"]
            asunto = form.cleaned_data["asunto"] or asunto_default
            mensaje = form.cleaned_data["mensaje"] or mensaje_default

            try:
                # Generar el PDF desde la URL real (Chrome Headless)
                pdf_bytes = generar_pdf_desde_url(url_completa)

                body_html = (
                    f"<p>{mensaje}</p>"
                    "<p style='margin-top:16px;'>"
                    "Bendiciones,<br><strong>Soid_Tf_2</strong>"
                    "</p>"
                )

                enviar_correo_sistema(
                    subject=asunto,
                    heading="Listado de nuevos creyentes",
                    body_html=body_html,
                    destinatarios=destinatario,
                    meta_text="Correo enviado desde Soid_Tf_2",
                    extra_context={"CFG": config},
                    adjuntos=[("nuevos_creyentes.pdf", pdf_bytes)],
                )

                messages.success(
                    request,
                    f"Correo enviado correctamente a {destinatario}."
                )
                return redirect("miembros_app:nuevo_creyente_lista")

            except Exception as e:
                messages.error(
                    request,
                    f"No se pudo enviar el correo: {e}",
                )
                return redirect("miembros_app:nuevo_creyente_lista")
    else:
        form = EnviarFichaMiembroEmailForm(
            initial={
                "destinatario": email_default,
                "asunto": asunto_default,
                "mensaje": mensaje_default,
            }
        )

    return render(
        request,
        "core/enviar_email.html",
        {
            "form": form,
            "titulo_pagina": "Enviar listado de nuevos creyentes",
            "descripcion": "Se generará un PDF idéntico al de impresión usando Chrome Headless.",
            "objeto_label": "Listado de nuevos creyentes",
            "url_cancelar": reverse("miembros_app:nuevo_creyente_lista"),
            "adjunto_auto_nombre": "nuevos_creyentes.pdf",
        },
    )
def exportar_miembros_excel(request):
    """
    Exporta a Excel los miembros que se están viendo en el listado,
    respetando TODOS los filtros aplicados en la vista miembro_lista.
    """

    # Base: solo miembros que NO son nuevos creyentes
    miembros_base = Miembro.objects.filter(nuevo_creyente=False)

    # Reutilizamos exactamente la misma lógica de filtros
    miembros, filtros_context = filtrar_miembros(request, miembros_base)

    # Creamos el libro de Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Miembros"

    # Encabezados de columnas
    headers = [
        "ID",
        "Nombres",
        "Apellidos",
        "Edad",
        "Género",
        "Estado",
        "Categoría edad",
        "Teléfono",
        "Email",
        "Bautizado",
        "Fecha ingreso",
        "Activo",
    ]
    ws.append(headers)

    # Rellenar filas con los datos filtrados
    for m in miembros:
        # Edad calculada (si no hay fecha de nacimiento, queda vacío)
        try:
            edad = m.edad
        except Exception:
            edad = None

        # Género, estado y categoría (usamos los display si existen)
        genero_display = (
            m.get_genero_display() if hasattr(m, "get_genero_display") else m.genero
        )
        estado_display = (
            m.get_estado_miembro_display()
            if hasattr(m, "get_estado_miembro_display")
            else m.estado_miembro
        )
        categoria_display = (
            m.get_categoria_edad_display()
            if hasattr(m, "get_categoria_edad_display")
            else m.categoria_edad
        )

        # Fecha de ingreso formateada
        if getattr(m, "fecha_ingreso_iglesia", None):
            fecha_ingreso_str = m.fecha_ingreso_iglesia.strftime("%d/%m/%Y")
        else:
            fecha_ingreso_str = ""

        row = [
            m.id,
            m.nombres,
            m.apellidos,
            edad if edad is not None else "",
            genero_display or "",
            estado_display or "",
            categoria_display or "",
            m.telefono or "",
            m.email or "",
            "Sí" if m.bautizado_confirmado else "No",
            fecha_ingreso_str,
            "Activo" if m.activo else "Inactivo",
        ]
        ws.append(row)

    # Ajustar un poco el ancho de las columnas automáticamente
    for column_cells in ws.columns:
        max_length = 0
        column = column_cells[0].column_letter  # A, B, C...
        for cell in column_cells:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
        # Limitar el ancho a algo razonable
        adjusted_width = min(max_length + 2, 40)
        ws.column_dimensions[column].width = adjusted_width

    # Preparar la respuesta HTTP con el archivo Excel
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = "miembros_filtrados.xlsx"

    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def importar_miembros_excel(request):
    """
    Importa miembros desde un archivo de Excel.
    Crea NUEVOS miembros usando las columnas del archivo.
    
    Formato esperado (fila 1 = encabezados):
    - Nombres
    - Apellidos
    - Genero       (Masculino / Femenino)
    - Estado       (Activo, Pasivo, En observación, En disciplina, Descarriado, Catecúmeno)
    - Telefono
    - Email
    - Fecha_nacimiento (dd/mm/aaaa o yyyy-mm-dd)
    """

    if request.method != "POST":
        messages.error(request, "Método no permitido para importar.")
        return redirect("miembros_app:lista")

    archivo = request.FILES.get("archivo_excel")

    if not archivo:
        messages.error(request, "No se ha enviado ningún archivo de Excel.")
        return redirect("miembros_app:lista")

    try:
        wb = load_workbook(filename=archivo, data_only=True)
        ws = wb.active
    except Exception as e:
        messages.error(request, f"El archivo no parece ser un Excel válido: {e}")
        return redirect("miembros_app:lista")

    # Leemos la fila de encabezados (fila 1)
    try:
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    except StopIteration:
        messages.error(request, "El archivo está vacío.")
        return redirect("miembros_app:lista")

    # Creamos un mapa nombre_columna -> índice
    header_map = {}
    for idx, name in enumerate(header_row):
        if name:
            key = str(name).strip().lower()
            header_map[key] = idx

    # Columnas mínimas obligatorias
    columnas_obligatorias = ["nombres", "apellidos"]
    faltantes = [col for col in columnas_obligatorias if col not in header_map]

    if faltantes:
        msg = (
            "Faltan columnas obligatorias en el encabezado: "
            + ", ".join(faltantes)
            + ". Asegúrate de tener al menos: Nombres y Apellidos."
        )
        messages.error(request, msg)
        return redirect("miembros_app:lista")

    creados = 0
    omitidos = 0

    # Mapeos para género y estado
    mapa_genero = {
        "masculino": "masculino",
        "m": "masculino",
        "hombre": "masculino",
        "male": "masculino",
        "femenino": "femenino",
        "f": "femenino",
        "mujer": "femenino",
        "female": "femenino",
    }

    mapa_estado = {
        "activo": "activo",
        "pasivo": "pasivo",
        "en observación": "observacion",
        "en observacion": "observacion",
        "observacion": "observacion",
        "observación": "observacion",
        "disciplina": "disciplina",
        "en disciplina": "disciplina",
        "descarriado": "descarriado",
        "catecumeno": "catecumeno",
        "catecúmeno": "catecumeno",
    }

    # Recorremos las filas de datos (desde la fila 2)
    for row in ws.iter_rows(min_row=2, values_only=True):
        # Si la fila está completamente vacía, la saltamos
        if not row or all((cell is None or str(cell).strip() == "") for cell in row):
            continue

        def get_value(nombre_col):
            idx = header_map.get(nombre_col)
            if idx is None:
                return ""
            value = row[idx]
            return "" if value is None else str(value).strip()

        nombres = get_value("nombres")
        apellidos = get_value("apellidos")

        if not nombres and not apellidos:
            # No tiene ni nombres ni apellidos, omitimos
            omitidos += 1
            continue

        genero_val = ""
        if "genero" in header_map:
            genero_raw = get_value("genero").lower()
            genero_val = mapa_genero.get(genero_raw, "")

        estado_val = "activo"
        if "estado" in header_map:
            estado_raw = get_value("estado").lower()
            estado_val = mapa_estado.get(estado_raw, "activo")

        telefono = get_value("telefono")
        email = get_value("email")

        fecha_nacimiento = None
        if "fecha_nacimiento" in header_map:
            valor_fecha = row[header_map["fecha_nacimiento"]]
            if valor_fecha:
                # Puede venir como fecha de Excel o como texto
                if hasattr(valor_fecha, "year"):
                    # Ya es un objeto date/datetime
                    try:
                        # Si es datetime, extraemos solo la fecha
                        fecha_nacimiento = valor_fecha.date()
                    except AttributeError:
                        fecha_nacimiento = valor_fecha
                else:
                    # Intentamos parsear texto
                    texto_fecha = str(valor_fecha).strip()
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            fecha_nacimiento = datetime.strptime(texto_fecha, fmt).date()
                            break
                        except ValueError:
                            continue

        # Creamos el miembro
        try:
            Miembro.objects.create(
                nombres=nombres,
                apellidos=apellidos,
                genero=genero_val,
                telefono=telefono,
                email=email,
                fecha_nacimiento=fecha_nacimiento,
                estado_miembro=estado_val,
                # El resto de campos quedan por defecto
            )
            creados += 1
        except Exception:
            omitidos += 1
            continue

    messages.success(
        request,
        f"Importación completada. Miembros creados: {creados}. Filas omitidas: {omitidos}.",
    )
    return redirect("miembros_app:lista")
