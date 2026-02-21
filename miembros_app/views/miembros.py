# -*- coding: utf-8 -*-
"""
miembros_app/views/miembros.py
Vistas CRUD de miembros: lista, crear, editar, detalle.
"""
from django.core.paginator import Paginator
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import DetailView, UpdateView
from django.views.decorators.http import require_GET
from django.urls import reverse
from django.db.models import Q, Sum

from miembros_app.models import Miembro, MiembroRelacion, sync_familia_inteligente_por_relacion
from miembros_app.forms import MiembroForm, MiembroRelacionForm
from core.utils_config import get_edad_minima_miembro_oficial
from notificaciones_app.utils import crear_notificacion
from finanzas_app.models import MovimientoFinanciero

from .utils import (
    calcular_edad,
    get_choices_safe,
    modulo_estructura_activo,
    miembro_tiene_asignacion_en_unidades,
    _safe_get_model,
    CORTE_NINOS,
)
from .familiares import calcular_parentescos_inferidos, obtener_relaciones_organizadas



# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN DE FILTRADO (compartida por lista y reportes)
# ═══════════════════════════════════════════════════════════════════════════════

def filtrar_miembros(request, miembros_base, para_paginacion=False):
    """
    Aplica todos los filtros del listado general de miembros.
    Devuelve: (miembros, filtros_context)
    
    Si para_paginacion=True, el filtro de rango de edad se hace en BD
    en lugar de en memoria (más eficiente para paginación).
    """
    hoy = date.today()
    
    # Leer parámetros
    query = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    categoria_edad_filtro = request.GET.get("categoria_edad", "").strip()
    genero = request.GET.get("genero", "").strip()
    bautizado = request.GET.get("bautizado", "").strip()
    rol_ministerial = request.GET.get("rol_ministerial", "").strip()
    estado_ministerial = request.GET.get("estado_ministerial", "").strip()
    tiene_credenciales_filtro = request.GET.get("tiene_credenciales", "").strip()
    tiene_contacto = request.GET.get("tiene_contacto", "") == "1"
    mostrar_todos = request.GET.get("mostrar_todos", "") == "1"
    incluir_ninos = request.GET.get("incluir_ninos", "") == "1"
    usar_rango_edad = request.GET.get("usar_rango_edad", "") == "1"
    
    edad_min_str = request.GET.get("edad_min", "").strip()
    edad_max_str = request.GET.get("edad_max", "").strip()
    
    edad_min = int(edad_min_str) if edad_min_str.isdigit() else None
    edad_max = int(edad_max_str) if edad_max_str.isdigit() else None

    miembros = miembros_base

    # Solo activos por defecto
    if not mostrar_todos:
        miembros = miembros.filter(activo=True)

    # Exclusión de niños
    cutoff_ninos = hoy - timedelta(days=CORTE_NINOS * 365)
    categorias_nino = ("infante", "nino")

    if not incluir_ninos and categoria_edad_filtro not in categorias_nino:
        miembros = miembros.filter(
            Q(fecha_nacimiento__lte=cutoff_ninos) | Q(fecha_nacimiento__isnull=True)
        )

    # Búsqueda general
    if query:
        miembros = miembros.filter(
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(telefono__icontains=query) |
            Q(email__icontains=query) |
            Q(cedula__icontains=query)
        )

    # Filtros simples
    if estado:
        miembros = miembros.filter(estado_miembro=estado)
    if genero:
        miembros = miembros.filter(genero=genero)
    if categoria_edad_filtro:
        miembros = miembros.filter(categoria_edad=categoria_edad_filtro)

    # Bautismo
    if bautizado == "1":
        miembros = miembros.filter(bautizado_confirmado=True)
    elif bautizado == "0":
        miembros = miembros.filter(
            Q(bautizado_confirmado=False) | Q(bautizado_confirmado__isnull=True)
        )

    # Filtros ministeriales
    if rol_ministerial:
        miembros = miembros.filter(rol_ministerial=rol_ministerial)
    if estado_ministerial:
        miembros = miembros.filter(estado_ministerial=estado_ministerial)
    if tiene_credenciales_filtro == "1":
        miembros = miembros.filter(tiene_credenciales=True)
    elif tiene_credenciales_filtro == "0":
        miembros = miembros.filter(tiene_credenciales=False)

    # Solo con contacto
    if tiene_contacto:
        miembros = miembros.filter(
            Q(telefono__isnull=False, telefono__gt="") |
            Q(telefono_secundario__isnull=False, telefono_secundario__gt="") |
            Q(email__isnull=False, email__gt="")
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # FILTRO POR RANGO DE EDAD - Optimizado para BD
    # ═══════════════════════════════════════════════════════════════════════════
    if usar_rango_edad and (edad_min is not None or edad_max is not None):
        if para_paginacion:
            # Filtrar en BD usando fecha_nacimiento (más eficiente)
            if edad_min is not None:
                # Para tener al menos edad_min años, debe haber nacido antes de esta fecha
                fecha_max_nacimiento = hoy - timedelta(days=edad_min * 365)
                miembros = miembros.filter(
                    fecha_nacimiento__isnull=False,
                    fecha_nacimiento__lte=fecha_max_nacimiento
                )
            if edad_max is not None:
                # Para tener como máximo edad_max años, debe haber nacido después de esta fecha
                fecha_min_nacimiento = hoy - timedelta(days=(edad_max + 1) * 365)
                miembros = miembros.filter(
                    fecha_nacimiento__gte=fecha_min_nacimiento
                )
        else:
            # Método original (para reportes PDF que necesitan todos los registros)
            miembros_filtrados = []
            for m in miembros:
                if not m.fecha_nacimiento:
                    continue
                edad = calcular_edad(m.fecha_nacimiento, hoy)
                if edad is None:
                    continue
                if edad_min is not None and edad < edad_min:
                    continue
                if edad_max is not None and edad > edad_max:
                    continue
                miembros_filtrados.append(m)
            miembros = miembros_filtrados

    # Orden base (solo si sigue siendo queryset)
    if hasattr(miembros, 'order_by'):
        miembros = miembros.order_by("nombres", "apellidos")

    # Choices para los selects
    filtros_context = {
        "query": query,
        "mostrar_todos": mostrar_todos,
        "incluir_ninos": incluir_ninos,
        "estado": estado,
        "categoria_edad_filtro": categoria_edad_filtro,
        "genero_filtro": genero,
        "bautizado": bautizado,
        "tiene_contacto": tiene_contacto,
        "estados_choices": get_choices_safe(Miembro, "estado_miembro"),
        "categorias_choices": get_choices_safe(Miembro, "categoria_edad"),
        "generos_choices": get_choices_safe(Miembro, "genero"),
        "usar_rango_edad": usar_rango_edad,
        "edad_min": edad_min_str,
        "edad_max": edad_max_str,
        "rol_ministerial": rol_ministerial,
        "estado_ministerial": estado_ministerial,
        "tiene_credenciales_filtro": tiene_credenciales_filtro,
        "roles_ministeriales_choices": [
            (k, v) for k, v in get_choices_safe(Miembro, "rol_ministerial") if k
        ],
        "estados_ministeriales_choices": [
            (k, v) for k, v in get_choices_safe(Miembro, "estado_ministerial") if k
        ],
    }

    return miembros, filtros_context


# ═══════════════════════════════════════════════════════════════════════════════
# LISTA DE MIEMBROS (CON PAGINACIÓN)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def miembro_lista(request):
    """Listado general de miembros con paginación (excluye nuevos creyentes)."""
    miembros_base = Miembro.objects.filter(nuevo_creyente=False)
    miembros_qs, filtros_context = filtrar_miembros(request, miembros_base, para_paginacion=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PAGINACIÓN
    # ═══════════════════════════════════════════════════════════════════════════
    items_por_pagina = 50  # Ajusta según necesites
    paginator = Paginator(miembros_qs, items_por_pagina)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except:
        page_obj = paginator.get_page(1)
    
    context = {
        "miembros": page_obj,  # Ahora es un Page object (iterable)
        "page_obj": page_obj,
        "paginator": paginator,
        "total_miembros": paginator.count,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": get_edad_minima_miembro_oficial(),
        "modo_pdf": False,
    }
    context.update(filtros_context)
    
    return render(request, "miembros_app/reportes/listado_miembros.html", context)


@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def miembro_lista_pdf(request):
    """Vista PDF del listado de miembros (sin paginación - trae todos)."""
    miembros_base = Miembro.objects.filter(nuevo_creyente=False)
    # para_paginacion=False para que traiga todos los registros
    miembros, filtros_context = filtrar_miembros(request, miembros_base, para_paginacion=False)
    
    context = {
        "miembros": miembros,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": get_edad_minima_miembro_oficial(),
        "modo_pdf": True,
    }
    context.update(filtros_context)
    
    return render(request, "miembros_app/reportes/listado_miembros_pdf.html", context)

# ═══════════════════════════════════════════════════════════════════════════════
# CREAR MIEMBRO
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.add_miembro", raise_exception=True)
def miembro_crear(request):
    """Vista para crear un nuevo miembro."""
    edad_minima = get_edad_minima_miembro_oficial()

    if request.method == "POST":
        form = MiembroForm(request.POST, request.FILES)
        
        if form.is_valid():
            miembro = form.save(commit=False)
            
            if not miembro.fecha_ingreso_iglesia:
                miembro.fecha_ingreso_iglesia = date.today()
            
            edad = calcular_edad(miembro.fecha_nacimiento)
            
            if edad is not None and edad < edad_minima:
                if miembro.estado_miembro:
                    miembro.estado_miembro = ""
                    messages.info(
                        request,
                        f"Este registro es menor de {edad_minima} años. Se ha guardado sin estado de miembro."
                    )
            
            miembro.save()
            
            # Notificación
            try:
                url_detalle = reverse("miembros_app:detalle", args=[miembro.pk])
                crear_notificacion(
                    usuario=request.user,
                    titulo="Nuevo miembro registrado",
                    mensaje=f"{miembro.nombres} {miembro.apellidos} ha sido añadido al sistema.",
                    url_name=url_detalle,
                    tipo="success",
                )
            except Exception as e:
                print("Error creando notificación:", e)
            
            if "guardar_y_nuevo" in request.POST:
                messages.success(request, "Miembro creado correctamente. Puedes registrar otro.")
                return redirect("miembros_app:crear")
            else:
                messages.success(request, "Miembro creado correctamente.")
                return redirect("miembros_app:lista")
        else:
            messages.error(request, "Hay errores en el formulario. Revisa los campos marcados en rojo.")
    else:
        form = MiembroForm()

    context = {
        "form": form,
        "modo": "crear",
        "miembro": None,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
    }
    
    return render(request, "miembros_app/miembro_form.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# EDITAR MIEMBRO (Class-Based View)
# ═══════════════════════════════════════════════════════════════════════════════

class MiembroUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "miembros_app.change_miembro"
    raise_exception = True
    model = Miembro
    form_class = MiembroForm
    template_name = "miembros_app/miembro_form.html"

    def _get_base_context(self, miembro, form):
        """Obtiene el contexto base para la vista de edición."""
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
        
        bloquear = miembro_tiene_asignacion_en_unidades(miembro)
        
        return {
            "form": form,
            "miembro": miembro,
            "rel_form": MiembroRelacionForm(),
            "modo": "editar",
            "todos_miembros": todos_miembros,
            "familiares": familiares_qs,
            "EDAD_MINIMA_MIEMBRO_OFICIAL": get_edad_minima_miembro_oficial(),
            "bloquear_estado": bloquear,
            "bloquear_identidad": bloquear,
            "TIPOS_RELACION_CHOICES": MiembroRelacion.TIPO_RELACION_CHOICES,
            "relaciones_inferidas": calcular_parentescos_inferidos(miembro),
        }

    def get(self, request, pk):
        miembro = get_object_or_404(Miembro, pk=pk)
        form = MiembroForm(instance=miembro)
        return render(request, self.template_name, self._get_base_context(miembro, form))

    def post(self, request, pk):
        miembro = get_object_or_404(Miembro, pk=pk)
        edad_minima = get_edad_minima_miembro_oficial()
        salida_antes = not miembro.activo and miembro.fecha_salida is not None

        # Agregar familiar
        if "agregar_familiar" in request.POST:
            rel_form = MiembroRelacionForm(request.POST, miembro=miembro)
            if rel_form.is_valid():
                relacion = rel_form.save(commit=False)
                relacion.miembro = miembro
                relacion.save()
                sync_familia_inteligente_por_relacion(relacion)
                messages.success(request, "Familiar agregado correctamente.")
            else:
                for field, errs in rel_form.errors.items():
                    for e in errs:
                        messages.error(request, f"{field}: {e}")
            return redirect(f"{request.path}?tab=familiares")

        # Guardado normal
        form = MiembroForm(request.POST, request.FILES, instance=miembro)

        if form.is_valid():
            miembro_editado = form.save(commit=False)

            # Verificar bloqueo de identidad
            genero_antes, fn_antes = miembro.genero, miembro.fecha_nacimiento
            genero_despues, fn_despues = miembro_editado.genero, miembro_editado.fecha_nacimiento
            
            cambio_identidad = (genero_antes != genero_despues) or (fn_antes != fn_despues)
            
            if cambio_identidad and miembro_tiene_asignacion_en_unidades(miembro):
                context = self._get_base_context(miembro, form)
                context["bloquear_identidad"] = True
                messages.error(
                    request,
                    "Acción bloqueada: no puedes cambiar género o fecha de nacimiento "
                    "mientras el miembro esté asignado a una o más unidades."
                )
                return render(request, self.template_name, context)

            miembro_editado.save()

            # Sincronizar familiares
            self._sincronizar_familiares(request, miembro_editado)

            # Notificación de salida
            salida_despues = not miembro_editado.activo and miembro_editado.fecha_salida is not None
            if not salida_antes and salida_despues:
                try:
                    crear_notificacion(
                        request.user,
                        titulo="Miembro dado de salida",
                        mensaje=f"Se ha dado salida al miembro {miembro_editado.nombres} {miembro_editado.apellidos}.",
                        url_name="miembros_app:detalle",
                        kwargs={"pk": miembro_editado.pk},
                        tipo="warning",
                    )
                except Exception:
                    pass

            messages.success(request, "Miembro actualizado correctamente.")
            return redirect("miembros_app:lista")

        return render(request, self.template_name, self._get_base_context(miembro, form))

    def _sincronizar_familiares(self, request, miembro):
        """Sincroniza las relaciones familiares desde el POST."""
        ids = request.POST.getlist("familiares_miembro_id[]")
        tipos = request.POST.getlist("familiares_tipo_relacion[]")
        vive_list = request.POST.getlist("familiares_vive_junto[]")
        resp_list = request.POST.getlist("familiares_es_responsable[]")
        notas_list = request.POST.getlist("familiares_notas[]")

        if not (len(ids) == len(tipos) == len(vive_list) == len(resp_list) == len(notas_list)):
            messages.error(request, "No se pudieron procesar los familiares: datos incompletos.")
            return

        payload = {}
        posted_ids = []

        for i in range(len(ids)):
            try:
                familiar_id = int(ids[i])
            except (TypeError, ValueError):
                continue

            if familiar_id == miembro.pk:
                messages.error(request, "No puedes asignar un miembro como familiar de sí mismo.")
                continue

            payload[familiar_id] = {
                "tipo_relacion": (tipos[i] or "otro").strip(),
                "vive_junto": vive_list[i] == "1",
                "es_responsable": resp_list[i] == "1",
                "notas": (notas_list[i] or "").strip(),
            }
            posted_ids.append(familiar_id)

        posted_set = set(posted_ids)
        existentes_qs = MiembroRelacion.objects.filter(miembro=miembro)
        existentes_set = set(existentes_qs.values_list("familiar_id", flat=True))

        # Eliminar los que ya no están
        a_borrar = existentes_set - posted_set
        if a_borrar:
            MiembroRelacion.objects.filter(miembro=miembro, familiar_id__in=a_borrar).delete()
            MiembroRelacion.objects.filter(miembro_id__in=a_borrar, familiar=miembro).delete()

        # Crear o actualizar
        for familiar_id, data in payload.items():
            rel, _ = MiembroRelacion.objects.update_or_create(
                miembro=miembro,
                familiar_id=familiar_id,
                defaults=data
            )

            tipo_inverso = MiembroRelacion.inverse_tipo(data["tipo_relacion"], miembro.genero)
            MiembroRelacion.objects.update_or_create(
                miembro_id=familiar_id,
                familiar=miembro,
                defaults={
                    "tipo_relacion": tipo_inverso,
                    "vive_junto": rel.vive_junto,
                    "es_responsable": False,
                    "notas": "",
                },
            )


# ═══════════════════════════════════════════════════════════════════════════════
# DETALLE MIEMBRO (Class-Based View)
# ═══════════════════════════════════════════════════════════════════════════════

class MiembroDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "miembros_app.view_miembro"
    raise_exception = True
    model = Miembro
    template_name = "miembros_app/miembros_detalle.html"

    def get(self, request, pk):
        miembro = get_object_or_404(Miembro, pk=pk)

        # Finanzas
        movimientos_financieros = (
            MovimientoFinanciero.objects
            .filter(persona_asociada=miembro)
            .exclude(estado="anulado")
            .order_by("-fecha", "-creado_en")
        )

        total_aportes = (
            movimientos_financieros
            .filter(tipo="ingreso")
            .aggregate(total=Sum("monto"))["total"] or 0
        )

        # Permisos
        can_dar_salida = request.user.has_perm("miembros_app.change_miembro")

        # Familia organizada
        relaciones_organizadas = obtener_relaciones_organizadas(miembro)

        context = {
            "miembro": miembro,
            **relaciones_organizadas,
            "EDAD_MINIMA_MIEMBRO_OFICIAL": get_edad_minima_miembro_oficial(),
            "movimientos_financieros": movimientos_financieros,
            "total_aportes": total_aportes,
            "can_dar_salida": can_dar_salida,
            "unidades_resumen": [],
            "unidades_total": 0,
            "privado_desbloqueado": request.session.get(f"miembro_privado_{pk}", False),
            "finanzas_desbloqueado": request.session.get(f"miembro_finanzas_{pk}", False),
        }

        # Unidades
        if modulo_estructura_activo():
            context.update(self._obtener_unidades_resumen(miembro))

        return render(request, self.template_name, context)

    def _obtener_unidades_resumen(self, miembro):
        """Obtiene el resumen de unidades del miembro."""
        UnidadCargo = _safe_get_model("estructura_app", "UnidadCargo")
        UnidadMembresia = _safe_get_model("estructura_app", "UnidadMembresia")

        if not (UnidadCargo and UnidadMembresia):
            return {"unidades_resumen": [], "unidades_total": 0}

        cargos_qs = (
            UnidadCargo.objects
            .filter(miembo_fk=miembro, vigente=True, unidad__activa=True)
            .select_related("unidad", "rol")
        )

        membresias_qs = (
            UnidadMembresia.objects
            .filter(miembo_fk=miembro, activo=True, unidad__activa=True)
            .select_related("unidad", "rol")
        )

        resumen = []
        vistos = set()

        for c in cargos_qs:
            key = ("CARGO", c.unidad_id, c.rol_id)
            if key in vistos:
                continue
            vistos.add(key)
            resumen.append({
                "unidad": c.unidad.nombre if c.unidad_id else "—",
                "rol": c.rol.nombre if c.rol_id else "Miembro",
                "tipo": "Liderazgo",
            })

        for m in membresias_qs:
            key = ("MEMB", m.unidad_id, m.rol_id)
            if key in vistos:
                continue
            vistos.add(key)
            rol_tipo = (m.rol.tipo or "").upper() if m.rol else ""
            resumen.append({
                "unidad": m.unidad.nombre if m.unidad_id else "—",
                "rol": m.rol.nombre if m.rol_id else "Miembro",
                "tipo": "Trabajo" if rol_tipo == "TRABAJO" else "Participación",
            })

        orden_tipo = {"Liderazgo": 0, "Participación": 1, "Trabajo": 2}
        resumen.sort(key=lambda x: (orden_tipo.get(x.get("tipo"), 99), x["unidad"], x["rol"]))

        return {"unidades_resumen": resumen, "unidades_total": len(resumen)}


# ═══════════════════════════════════════════════════════════════════════════════
# FICHA DEL MIEMBRO
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def miembro_ficha(request, pk):
    """Ficha pastoral imprimible para un miembro."""
    miembro = get_object_or_404(Miembro, pk=pk)

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

    context = {
        "miembro": miembro,
        "relaciones_familia": relaciones_familia,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": get_edad_minima_miembro_oficial(),
    }

    return render(request, "miembros_app/reportes/miembro_ficha.html", context)