from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Q, Count
from django.contrib import messages
from django.urls import reverse   # 👈 IMPORTANTE: necesario para eliminar_familiar
from datetime import date, timedelta
from .models import Miembro, MiembroRelacion
from .forms import MiembroForm, MiembroRelacionForm
from datetime import date
from django.utils import timezone




# -------------------------------------
# DASHBOARD
# -------------------------------------
# -------------------------------------
# DASHBOARD DE MIEMBROS
# -------------------------------------
# -------------------------------------
# DASHBOARD DE MIEMBROS
# -------------------------------------
def miembros_dashboard(request):
    miembros = Miembro.objects.all()

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
    # (solo >= 12 años)
    # -----------------------------
    activos = 0
    pasivos = 0
    descarriados = 0
    observacion = 0

    for m in miembros:
        edad = calcular_edad(m.fecha_nacimiento)
        if edad is None or edad < 12:
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
        "descripcion_pagina": "Resumen de la membresía oficial (mayores de 12 años) y distribución general.",
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
    }
    return render(request, "miembros_app/miembros_dashboard.html", context)


# -------------------------------------
# FUNCIÓN AUXILIAR DE FILTRO DE MIEMBROS
# -------------------------------------
# -------------------------------------
# FUNCIÓN AUXILIAR DE FILTRO DE MIEMBROS
# -------------------------------------
def filtrar_miembros(request):
    """
    Aplica filtros comunes a las vistas de lista y reportes,
    y devuelve (queryset_filtrado, contexto_filtros).

    Reglas:

    - Por defecto (sin 'mostrar_todos' y sin 'estado'):
        * activo = True
        * estado_miembro en ('activo', 'pasivo')
        * edad >= 12 años (no niños)

    - Si se marca 'mostrar_todos':
        * NO se filtra por campo activo (aparecen también los que se fueron)
        * Si NO hay estado elegido -> se muestran TODOS los estados
          (activo, pasivo, catecúmeno, descarriado, observación, etc.)
        * Si hay un estado elegido -> solo ese estado.

    - 'incluir_ninos' solo se aplica cuando NO se ha elegido un estado.
      Nunca se mezclarán niños con catecúmenos, descarriados, etc.

    - Si la categoría de edad filtrada es de niños ('infante' o 'nino'),
      se devuelve SOLO el listado de niños (no adultos),
      aunque no se haya marcado 'incluir_ninos', y solo si NO hay estado elegido.
    """
    query = request.GET.get("q", "").strip()
    mostrar_todos = request.GET.get("mostrar_todos") == "1"
    incluir_ninos = request.GET.get("incluir_ninos") == "1"

    # Filtros avanzados
    estado = request.GET.get("estado", "").strip()
    categoria_edad_filtro = request.GET.get("categoria_edad", "").strip()
    genero = request.GET.get("genero", "").strip()
    bautizado = request.GET.get("bautizado", "").strip()  # "1", "0" o ""
    tiene_contacto = request.GET.get("tiene_contacto") == "1"

    miembros_base = Miembro.objects.all()

    # -------------------------
    # FILTRO POR ACTIVO / INACTIVO (CAMPO 'activo')
    # -------------------------
    if not mostrar_todos:
        # Vista por defecto: solo miembros que siguen activos en Torre Fuerte
        miembros_base = miembros_base.filter(activo=True)

    # -------------------------
    # FILTROS GENERALES (SE APLICAN A TODO: ADULTOS Y NIÑOS)
    # -------------------------
    if genero:
        miembros_base = miembros_base.filter(genero=genero)

    if bautizado == "1":
        miembros_base = miembros_base.filter(bautizado_confirmado=True)
    elif bautizado == "0":
        miembros_base = miembros_base.filter(bautizado_confirmado=False)

    if tiene_contacto:
        miembros_base = miembros_base.filter(
            Q(telefono__isnull=False, telefono__gt="")
            | Q(email__isnull=False, email__gt="")
        )

    if query:
        miembros_base = miembros_base.filter(
            Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(email__icontains=query)
            | Q(telefono__icontains=query)
            | Q(telefono_secundario__icontains=query)
        )

    # -------------------------
    # CÁLCULO EDAD (OFICIALES vs NIÑOS)
    # -------------------------
    today = timezone.localdate()
    cutoff_12 = today - timedelta(days=12 * 365)

    edad_oficial_q = Q(fecha_nacimiento__lte=cutoff_12) | Q(
        fecha_nacimiento__isnull=True
    )
    edad_nino_q = Q(fecha_nacimiento__gt=cutoff_12)

    # Partimos de la base ya filtrada (búsqueda, género, contacto, etc.)
    miembros_oficiales = miembros_base.filter(edad_oficial_q)
    miembros_ninos = miembros_base.filter(edad_nino_q)

    # Categorías que consideramos "de niños"
    categorias_nino = ("infante", "nino")

    # -------------------------
    # LÓGICA DE ESTADO Y CATEGORÍA
    # -------------------------
    if estado:
        # Si hay estado elegido:
        #  - SOLO se muestran mayores de 12 con ese estado
        #  - Nunca se añaden niños
        miembros_oficiales = miembros_oficiales.filter(estado_miembro=estado)
        # Si además filtraron por categoría, se aplica solo a oficiales
        if categoria_edad_filtro and categoria_edad_filtro not in categorias_nino:
            miembros_oficiales = miembros_oficiales.filter(
                categoria_edad=categoria_edad_filtro
            )
        # Si la categoría es niño/infante + estado, no devolvemos niños ni adultos con esa categoría
        mostrar_ninos = False

    else:
        # SIN estado elegido
        if categoria_edad_filtro in categorias_nino:
            # Si se pidió explícitamente "Infante" o "Niño" sin estado:
            #  -> devolver SOLO niños de esa categoría
            miembros_oficiales = miembros_oficiales.none()
            miembros_ninos = miembros_ninos.filter(
                categoria_edad=categoria_edad_filtro
            )
            mostrar_ninos = True
        else:
            # Categoría NO es de niños (o no se eligió categoría)
            if categoria_edad_filtro:
                # Filtramos por categoría (adolescente, joven, adulto, adulto_mayor...)
                miembros_oficiales = miembros_oficiales.filter(
                    categoria_edad=categoria_edad_filtro
                )
                miembros_ninos = miembros_ninos.filter(
                    categoria_edad=categoria_edad_filtro
                )

            # Ahora aplicamos la lógica de estados según 'mostrar_todos'
            if mostrar_todos:
                # Estado vacío + mostrar_todos marcado:
                # -> mostrar todos los estados posibles (no filtramos estado_miembro)
                pass
            else:
                # Vista normal por defecto: solo ACTIVO y PASIVO
                miembros_oficiales = miembros_oficiales.filter(
                    estado_miembro__in=["activo", "pasivo"]
                )

            # En este caso (sin estado y sin categoría de niños),
            # SÍ respetamos el checkbox "incluir_ninos"
            mostrar_ninos = incluir_ninos

    # -------------------------
    # COMBINACIÓN FINAL (ADULTOS + NIÑOS)
    # -------------------------
    if mostrar_ninos:
        miembros = miembros_oficiales | miembros_ninos
    else:
        miembros = miembros_oficiales

    miembros = miembros.order_by("nombres", "apellidos")

    # -------------------------
    # CHOICES PARA LOS SELECTS
    # -------------------------
    campo_estado = Miembro._meta.get_field("estado_miembro")
    estados_choices = list(campo_estado.flatchoices)

    campo_categoria = Miembro._meta.get_field("categoria_edad")
    categorias_choices = list(campo_categoria.flatchoices)

    try:
        campo_genero = Miembro._meta.get_field("genero")
        generos_choices = list(campo_genero.flatchoices)
    except Exception:
        generos_choices = []

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
    }

    return miembros, filtros_context


# -------------------------------------
# LISTA DE MIEMBROS
# -------------------------------------
def miembro_lista(request):
    miembros, filtros_context = filtrar_miembros(request)

    context = {
        "miembros": miembros,
        **filtros_context,
    }
    return render(request, "miembros_app/miembros_lista.html", context)


# -------------------------------------
# CREAR MIEMBRO
# -------------------------------------
def miembro_crear(request):
    if request.method == "POST":
        form = MiembroForm(request.POST, request.FILES)
        if form.is_valid():
            # No guardamos todavía, para poder ajustar el estado
            miembro = form.save(commit=False)

            # Usamos el propio método del modelo para calcular la edad
            edad = miembro.calcular_edad()

            # Si es menor de 12 años, se guarda SIN estado de miembro
            if edad is not None and edad < 12:
                if miembro.estado_miembro:
                    miembro.estado_miembro = ""  # sin estado
                    messages.info(
                        request,
                        "Este registro es menor de 12 años. "
                        "Se ha guardado sin estado de miembro, ya que aún no es miembro oficial."
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
    }
    return render(request, "miembros_app/miembro_form.html", context)


# -------------------------------------
# EDITAR MIEMBRO
# -------------------------------------
class MiembroUpdateView(View):
    def get(self, request, pk):
        miembro = get_object_or_404(Miembro, pk=pk)
        form = MiembroForm(instance=miembro)

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
        }
        return render(request, "miembros_app/miembro_form.html", context)

    def post(self, request, pk):
        miembro = get_object_or_404(Miembro, pk=pk)

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

            # Lógica de edad: si es menor de 12 años, se guarda SIN estado de miembro
            edad = None
            if miembro_editado.fecha_nacimiento:
                hoy = date.today()
                fn = miembro_editado.fecha_nacimiento
                edad = hoy.year - fn.year
                if (hoy.month, hoy.day) < (fn.month, fn.day):
                    edad -= 1

            if edad is not None and edad < 12:
                if miembro_editado.estado_miembro:
                    miembro_editado.estado_miembro = ""  # sin estado
                    messages.info(
                        request,
                        "Este miembro es menor de 12 años. "
                        "Se ha guardado sin estado de miembro para no contarlo como miembro oficial."
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

        context = {
            "miembro": miembro,
            "relaciones_familia": relaciones_familia,
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
from django.urls import reverse  # asegúrate de tener este import arriba

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

    context = {
        "miembro": miembro,
        "relaciones_familia": relaciones_familia,
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
    miembros, filtros_context = filtrar_miembros(request)

    context = {
        "miembros": miembros,
        **filtros_context,
    }
    return render(request, "miembros_app/reportes/listado_miembros.html", context)



# -------------------------------------
# REPORTE: FICHA PASTORAL DEL MIEMBRO
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

    context = {
        "miembro": miembro,
        "relaciones_familia": relaciones_familia,
    }

    return render(request, "miembros_app/reportes/miembro_ficha.html", context)

