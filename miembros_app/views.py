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

from .models import Miembro, MiembroRelacion, RazonSalidaMiembro
from .forms import MiembroForm, MiembroRelacionForm

from core.utils_config import get_edad_minima_miembro_oficial
from django.http import HttpResponse
import traceback



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
    # Conteo de miembros oficiales
    # (solo >= edad_minima)
    # -----------------------------
    activos = 0
    pasivos = 0
    descarriados = 0
    observacion = 0

    for m in miembros:
        edad = calcular_edad(m.fecha_nacimiento)
        if edad is None or edad < edad_minima:
            # No se considera miembro oficial
            continue

        if m.estado_miembro == "activo":
            activos += 1
        elif m.estado_miembro == "pasivo":
            pasivos += 1
        elif m.estado_miembro == "descarriado":
            descarriados += 1
        elif m.estado_miembro == "observacion":
            observacion += 1

    total_oficiales = activos + pasivos + descarriados + observacion

    def porcentaje(cantidad):
        if total_oficiales == 0:
            return 0
        return round((cantidad * 100) / total_oficiales)

    # -----------------------------
    # Distribución por etapa de vida
    # (usa a TODOS los miembros)
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
    limite = hoy + timedelta(days=30)
    proximos_cumpleanos = []

    for m in miembros.filter(fecha_nacimiento__isnull=False):
        fn = m.fecha_nacimiento
        # Próximo cumpleaños en este año
        try:
            proximo = fn.replace(year=hoy.year)
        except ValueError:
            # Por si es 29 de febrero
            proximo = fn.replace(year=hoy.year, day=28)

        if proximo < hoy:
            try:
                proximo = proximo.replace(year=hoy.year + 1)
            except ValueError:
                proximo = proximo.replace(year=hoy.year + 1, day=28)

        if hoy <= proximo <= limite:
            edad_proxima = calcular_edad(fn) or ""
            proximos_cumpleanos.append(
                {
                    "nombre": f"{m.nombres} {m.apellidos}",
                    "fecha": proximo,
                    "edad": edad_proxima,
                }
            )

    proximos_cumpleanos.sort(key=lambda x: x["fecha"])
    proximos_cumpleanos = proximos_cumpleanos[:5]

    # -----------------------------
    # Miembros recientes
    # -----------------------------
    try:
        miembros_recientes = miembros.order_by(
            "-fecha_ingreso_iglesia", "-fecha_creacion"
        )[:5]
    except Exception:
        # Por si no existiera fecha_creacion en el modelo
        miembros_recientes = miembros.order_by("-fecha_ingreso_iglesia", "-id")[:5]

    context = {
        "titulo_pagina": "Miembros",
        "descripcion_pagina": (
            f"Resumen de la membresía oficial "
            f"(mayores de {edad_minima} años) y distribución general."
        ),
        # Tarjetas oficiales
        "total_oficiales": total_oficiales,
        "activos": activos,
        "pasivos": pasivos,
        "descarriados": descarriados,
        "observacion": observacion,
        "pct_activos": porcentaje(activos),
        "pct_pasivos": porcentaje(pasivos),
        "pct_descarriados": porcentaje(descarriados),
        "pct_observacion": porcentaje(observacion),
        # Gráfico y listas
        "total_miembros": total_miembros,
        "distribucion_etapa_vida": distribucion_etapa_vida,
        "proximos_cumpleanos": proximos_cumpleanos,
        "miembros_recientes": miembros_recientes,
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
    """
    miembros_base = Miembro.objects.all()

    miembros, filtros_context = filtrar_miembros(request, miembros_base)

    # Edad mínima oficial para mostrar en el texto de la plantilla
    edad_minima = get_edad_minima_miembro_oficial()

    context = {
        "miembros": miembros,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
    }
    # Mezclamos con todos los filtros (para que el formulario recuerde el estado)
    context.update(filtros_context)

    return render(
        request,
        "miembros_app/reportes/listado_miembros.html",
        context,
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

            messages.success(request, "Miembro creado correctamente.")
            return redirect("miembros_app:editar", pk=miembro.pk)

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
def reporte_relaciones_familiares(request):
    """
    Reporte de relaciones familiares entre miembros.
    Muestra quién está relacionado con quién (cónyuges, hijos, etc.).
    """

    query = request.GET.get("q", "").strip()
    solo_miembros = request.GET.get("solo_miembros", "") == "1"

    # Traemos todas las relaciones, incluyendo los datos del miembro y del familiar
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

    # Opcional: solo relaciones donde el familiar también es miembro registrado
    if solo_miembros:
        relaciones = relaciones.filter(familiar__isnull=False)

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
