# -*- coding: utf-8 -*-
"""
miembros_app/views/familiares.py

Vistas para gestión de relaciones familiares.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q

from miembros_app.models import Miembro, MiembroRelacion
from miembros_app.validators import validar_relacion_familiar


from .utils import (
    TIPOS_NUCLEAR,
    TIPOS_ORIGEN,
    TIPOS_EXTENDIDA,
    TIPOS_POLITICA,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

TIPOS_RELACION = MiembroRelacion.TIPO_RELACION_CHOICES


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def _obtener_relaciones_directas(miembro_id):
    """
    Obtiene todas las relaciones directas de un miembro, normalizadas.
    """
    padres = set()
    hijos = set()
    hermanos = set()
    conyuges = set()
    
    rels = (
        MiembroRelacion.objects
        .filter(Q(miembro_id=miembro_id) | Q(familiar_id=miembro_id))
        .select_related("miembro", "familiar")
    )
    
    for rel in rels:
        if rel.miembro_id == miembro_id:
            otro_id = rel.familiar_id
            tipo = rel.tipo_relacion
        else:
            otro_id = rel.miembro_id
            tipo = MiembroRelacion.inverse_tipo(rel.tipo_relacion, rel.miembro.genero)
        
        if tipo in ("padre", "madre"):
            padres.add(otro_id)
        elif tipo == "hijo":
            hijos.add(otro_id)
        elif tipo == "hermano":
            hermanos.add(otro_id)
        elif tipo == "conyuge":
            conyuges.add(otro_id)
    
    return {
        "padres": padres,
        "hijos": hijos,
        "hermanos": hermanos,
        "conyuges": conyuges,
    }


def _obtener_padres_completos(miembro_id, cache=None):
    """Obtiene TODOS los padres de un miembro (directos + inferidos por cónyuge)."""
    if cache is None:
        cache = {}
    
    cache_key = f"padres_{miembro_id}"
    if cache_key in cache:
        return cache[cache_key]
    
    rels = _obtener_relaciones_directas(miembro_id)
    padres_directos = rels["padres"]
    padres_inferidos = set()
    
    if padres_directos:
        rels_padres = (
            MiembroRelacion.objects
            .filter(
                Q(miembro_id__in=padres_directos, tipo_relacion="conyuge") |
                Q(familiar_id__in=padres_directos, tipo_relacion="conyuge")
            )
        )
        
        for rel in rels_padres:
            conyuge_id = rel.familiar_id if rel.miembro_id in padres_directos else rel.miembro_id
            if conyuge_id not in padres_directos and conyuge_id != miembro_id:
                padres_inferidos.add(conyuge_id)
    
    resultado = (padres_directos, padres_inferidos)
    cache[cache_key] = resultado
    return resultado


def _obtener_hijos_completos(miembro_id, cache=None):
    """Obtiene TODOS los hijos de un miembro (directos + inferidos por cónyuge)."""
    if cache is None:
        cache = {}
    
    cache_key = f"hijos_{miembro_id}"
    if cache_key in cache:
        return cache[cache_key]
    
    rels = _obtener_relaciones_directas(miembro_id)
    hijos_directos = rels["hijos"]
    conyuges = rels["conyuges"]
    hijos_inferidos = set()
    
    if conyuges:
        for conyuge_id in conyuges:
            rels_conyuge = _obtener_relaciones_directas(conyuge_id)
            hijos_conyuge = rels_conyuge["hijos"]
            for hijo_id in hijos_conyuge:
                if hijo_id not in hijos_directos and hijo_id != miembro_id:
                    hijos_inferidos.add(hijo_id)
    
    resultado = (hijos_directos, hijos_inferidos)
    cache[cache_key] = resultado
    return resultado


def _obtener_hermanos_completos(miembro_id, todos_padres_ids):
    """Obtiene todos los hermanos (personas que comparten al menos un padre)."""
    hermanos = set()
    
    if not todos_padres_ids:
        return hermanos
    
    hermanos = set(
        MiembroRelacion.objects
        .filter(tipo_relacion__in=["padre", "madre"], familiar_id__in=todos_padres_ids)
        .exclude(miembro_id=miembro_id)
        .values_list("miembro_id", flat=True)
    )
    
    hijos_de_padres = set(
        MiembroRelacion.objects
        .filter(miembro_id__in=todos_padres_ids, tipo_relacion="hijo")
        .exclude(familiar_id=miembro_id)
        .values_list("familiar_id", flat=True)
    )
    
    hermanos |= hijos_de_padres
    return hermanos


def calcular_parentescos_inferidos(miembro):
    """Calcula TODOS los parentescos inferidos de un miembro."""
    mi_id = miembro.id
    cache = {}

    mis_rels = _obtener_relaciones_directas(mi_id)
    padres_directos = mis_rels["padres"]
    hijos_directos = mis_rels["hijos"]
    hermanos_directos = mis_rels["hermanos"]
    conyuges_directos = mis_rels["conyuges"]

    padres_dir, padres_inf = _obtener_padres_completos(mi_id, cache)
    todos_mis_padres = padres_dir | padres_inf

    hijos_dir, hijos_inf = _obtener_hijos_completos(mi_id, cache)
    todos_mis_hijos = hijos_dir | hijos_inf

    hermanos_inferidos = _obtener_hermanos_completos(mi_id, todos_mis_padres)
    hermanos_inferidos |= hermanos_directos
    todos_mis_hermanos = hermanos_inferidos.copy()

    # Abuelos
    abuelos_ids = set()
    for padre_id in todos_mis_padres:
        p_dir, p_inf = _obtener_padres_completos(padre_id, cache)
        abuelos_ids |= p_dir | p_inf

    # Tíos
    tios_ids = set()
    for padre_id in todos_mis_padres:
        p_dir, p_inf = _obtener_padres_completos(padre_id, cache)
        abuelos_linea = p_dir | p_inf
        hermanos_del_padre = _obtener_hermanos_completos(padre_id, abuelos_linea)
        tios_ids |= hermanos_del_padre

    # Sobrinos
    sobrinos_ids = set()
    for hermano_id in todos_mis_hermanos:
        h_dir, h_inf = _obtener_hijos_completos(hermano_id, cache)
        sobrinos_ids |= h_dir | h_inf

    # Primos
    primos_ids = set()
    for tio_id in tios_ids:
        h_dir, h_inf = _obtener_hijos_completos(tio_id, cache)
        primos_ids |= h_dir | h_inf

    # Nietos
    nietos_ids = set()
    for hijo_id in todos_mis_hijos:
        h_dir, h_inf = _obtener_hijos_completos(hijo_id, cache)
        nietos_ids |= h_dir | h_inf

    # Cuñados
    cunados_ids = set()
    for hermano_id in todos_mis_hermanos:
        rels_hermano = _obtener_relaciones_directas(hermano_id)
        cunados_ids |= rels_hermano["conyuges"]
    
    for conyuge_id in conyuges_directos:
        p_dir, p_inf = _obtener_padres_completos(conyuge_id, cache)
        hermanos_conyuge = _obtener_hermanos_completos(conyuge_id, p_dir | p_inf)
        cunados_ids |= hermanos_conyuge

    # Suegros
    suegros_ids = set()
    for conyuge_id in conyuges_directos:
        p_dir, p_inf = _obtener_padres_completos(conyuge_id, cache)
        suegros_ids |= p_dir | p_inf

    # Yernos/Nueras
    yernos_ids = set()
    for hijo_id in todos_mis_hijos:
        rels_hijo = _obtener_relaciones_directas(hijo_id)
        yernos_ids |= rels_hijo["conyuges"]

    # Consuegros
    consuegros_ids = set()
    for yerno_id in yernos_ids:
        p_dir, p_inf = _obtener_padres_completos(yerno_id, cache)
        consuegros_ids |= p_dir | p_inf

    # Bisabuelos
    bisabuelos_ids = set()
    for abuelo_id in abuelos_ids:
        p_dir, p_inf = _obtener_padres_completos(abuelo_id, cache)
        bisabuelos_ids |= p_dir | p_inf

    # Bisnietos
    bisnietos_ids = set()
    for nieto_id in nietos_ids:
        h_dir, h_inf = _obtener_hijos_completos(nieto_id, cache)
        bisnietos_ids |= h_dir | h_inf

    # Limpieza
    ids_directos = padres_directos | hijos_directos | hermanos_directos | conyuges_directos
    
    todos_sets = [
        padres_inf, hijos_inf, hermanos_inferidos, abuelos_ids, tios_ids,
        sobrinos_ids, primos_ids, nietos_ids, cunados_ids, suegros_ids,
        yernos_ids, consuegros_ids, bisabuelos_ids, bisnietos_ids
    ]
    
    for s in todos_sets:
        s.discard(mi_id)
        s -= ids_directos
    
    hermanos_inferidos -= hermanos_directos

    # Construir resultado
    ids_total = set()
    for s in todos_sets:
        ids_total |= s
    
    miembros_map = {
        m.id: m 
        for m in Miembro.objects.filter(id__in=ids_total).only("id", "nombres", "apellidos", "genero", "foto")
    }

    def pack(ids_set, tipo, razon=""):
        return [
            {
                "otro": miembros_map[mid],
                "tipo": tipo,
                "tipo_label": MiembroRelacion.label_por_genero(tipo, miembros_map[mid].genero),
                "inferido": True,
                "razon": razon,
            }
            for mid in ids_set if mid in miembros_map
        ]

    inferidos = []
    inferidos += pack(padres_inf, "padre", "Cónyuge de tu padre/madre")
    inferidos += pack(hijos_inf, "hijo", "Hijo/a de tu cónyuge")
    inferidos += pack(hermanos_inferidos, "hermano", "Comparten padre/madre")
    inferidos += pack(abuelos_ids, "abuelo", "Padre/madre de tu padre/madre")
    inferidos += pack(bisabuelos_ids, "bisabuelo", "Padre/madre de tu abuelo/a")
    inferidos += pack(tios_ids, "tio", "Hermano/a de tu padre/madre")
    inferidos += pack(sobrinos_ids, "sobrino", "Hijo/a de tu hermano/a")
    inferidos += pack(primos_ids, "primo", "Hijo/a de tu tío/a")
    inferidos += pack(nietos_ids, "nieto", "Hijo/a de tu hijo/a")
    inferidos += pack(bisnietos_ids, "bisnieto", "Hijo/a de tu nieto/a")
    inferidos += pack(cunados_ids, "cunado", "Cónyuge de hermano/a o hermano/a de cónyuge")
    inferidos += pack(suegros_ids, "suegro", "Padre/madre de tu cónyuge")
    inferidos += pack(yernos_ids, "yerno", "Cónyuge de tu hijo/a")
    inferidos += pack(consuegros_ids, "consuegro", "Padre/madre del cónyuge de tu hijo/a")

    return inferidos


def obtener_relaciones_organizadas(miembro):
    """Obtiene todas las relaciones del miembro organizadas en 4 categorías."""
    mi_id = miembro.id
    
    relaciones_qs = (
        MiembroRelacion.objects
        .filter(Q(miembro_id=mi_id) | Q(familiar_id=mi_id))
        .select_related("miembro", "familiar")
    )
    
    familia_nuclear = []
    familia_origen = []
    familia_extendida = []
    familia_politica = []
    
    ids_agregados = set()
    
    for rel in relaciones_qs:
        if rel.miembro_id == mi_id:
            otro = rel.familiar
            tipo = rel.tipo_relacion
            relacion_id = rel.id
        else:
            otro = rel.miembro
            tipo = MiembroRelacion.inverse_tipo(rel.tipo_relacion, rel.miembro.genero)
            relacion_id = rel.id
        
        if otro.id in ids_agregados:
            continue
        ids_agregados.add(otro.id)
        
        dato = {
            "otro": otro,
            "tipo": tipo,
            "tipo_label": MiembroRelacion.label_por_genero(tipo, otro.genero),
            "vive_junto": rel.vive_junto,
            "es_responsable": rel.es_responsable,
            "notas": rel.notas,
            "relacion_id": relacion_id,
        }
        
        if tipo in TIPOS_NUCLEAR:
            familia_nuclear.append(dato)
        elif tipo in TIPOS_ORIGEN:
            familia_origen.append(dato)
        elif tipo in TIPOS_EXTENDIDA:
            familia_extendida.append(dato)
        elif tipo in TIPOS_POLITICA:
            familia_politica.append(dato)
    
    # Ordenar
    orden = {
        "conyuge": 0, "hijo": 1,
        "padre": 0, "madre": 1, "hermano": 2,
        "abuelo": 0, "bisabuelo": 1, "tio": 2, "primo": 3, "sobrino": 4, "nieto": 5, "bisnieto": 6,
        "suegro": 0, "cunado": 1, "yerno": 2, "consuegro": 3,
    }
    
    for lista in (familia_nuclear, familia_origen, familia_extendida, familia_politica):
        lista.sort(key=lambda r: orden.get(r["tipo"], 99))
    
    return {
        "familia_nuclear": familia_nuclear,
        "familia_origen": familia_origen,
        "familia_extendida": familia_extendida,
        "familia_politica": familia_politica,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# VISTAS PRINCIPALES
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.view_miembro", raise_exception=True)
def familiares_lista(request, pk):
    """Lista todos los familiares de un miembro."""
    miembro = get_object_or_404(Miembro, pk=pk)
    
    # Obtener relaciones organizadas
    relaciones = obtener_relaciones_organizadas(miembro)
    
    # Obtener inferidos
    inferidos = calcular_parentescos_inferidos(miembro)
    
    context = {
        "miembro": miembro,
        "familia_nuclear": relaciones["familia_nuclear"],
        "familia_origen": relaciones["familia_origen"],
        "familia_extendida": relaciones["familia_extendida"],
        "familia_politica": relaciones["familia_politica"],
        "inferidos": inferidos,
    }
    
    return render(request, "miembros_app/familiares/lista.html", context)


@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
def familiares_agregar(request, pk):
    """Formulario para agregar un familiar."""
    miembro = get_object_or_404(Miembro, pk=pk)
    
    if request.method == "POST":
        familiar_id = request.POST.get("familiar")
        tipo_relacion = request.POST.get("tipo_relacion")
        vive_junto = request.POST.get("vive_junto") == "on"
        es_responsable = request.POST.get("es_responsable") == "on"
        notas = request.POST.get("notas", "").strip()
        
        # Validar campos requeridos
        if not familiar_id or not tipo_relacion:
            messages.error(request, "Debe seleccionar un familiar y tipo de relación.")
            return redirect("miembros_app:familiares_agregar", pk=pk)
        
        try:
            familiar = Miembro.objects.get(pk=familiar_id)
        except Miembro.DoesNotExist:
            messages.error(request, "El familiar seleccionado no existe.")
            return redirect("miembros_app:familiares_agregar", pk=pk)
        
        # Crear relación
        MiembroRelacion.objects.create(
            miembro=miembro,
            familiar=familiar,
            tipo_relacion=tipo_relacion,
            vive_junto=vive_junto,
            es_responsable=es_responsable,
            notas=notas,
        )
        
        messages.success(request, f"Se agregó a {familiar.nombres} {familiar.apellidos} como {tipo_relacion}.")
        return redirect("miembros_app:familiares_lista", pk=pk)
    
    context = {
        "miembro": miembro,
        "TIPOS_RELACION": TIPOS_RELACION,
        "form": {},  # Placeholder para errores
    }
    
    return render(request, "miembros_app/familiares/agregar.html", context)


@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
def familiares_editar(request, pk, relacion_id):
    """Formulario para editar una relación familiar."""
    miembro = get_object_or_404(Miembro, pk=pk)
    relacion = get_object_or_404(MiembroRelacion, pk=relacion_id)
    
    # Verificar que la relación pertenece al miembro
    if relacion.miembro_id != miembro.id and relacion.familiar_id != miembro.id:
        messages.error(request, "La relación no pertenece a este miembro.")
        return redirect("miembros_app:familiares_lista", pk=pk)
    
    if request.method == "POST":
        tipo_relacion = request.POST.get("tipo_relacion")
        vive_junto = request.POST.get("vive_junto") == "on"
        es_responsable = request.POST.get("es_responsable") == "on"
        notas = request.POST.get("notas", "").strip()
        
        if not tipo_relacion:
            messages.error(request, "Debe seleccionar el tipo de relación.")
            return redirect("miembros_app:familiares_editar", pk=pk, relacion_id=relacion_id)
        
        relacion.tipo_relacion = tipo_relacion
        relacion.vive_junto = vive_junto
        relacion.es_responsable = es_responsable
        relacion.notas = notas
        relacion.save()
        
        messages.success(request, "Relación actualizada correctamente.")
        return redirect("miembros_app:familiares_lista", pk=pk)
    
    context = {
        "miembro": miembro,
        "relacion": relacion,
        "TIPOS_RELACION": TIPOS_RELACION,
    }
    
    return render(request, "miembros_app/familiares/editar.html", context)


@login_required
@require_POST
@permission_required("miembros_app.delete_miembrorelacion", raise_exception=True)
def familiares_eliminar(request, pk, relacion_id):
    """Elimina una relación familiar."""
    miembro = get_object_or_404(Miembro, pk=pk)
    relacion = get_object_or_404(MiembroRelacion, pk=relacion_id)
    
    # Verificar que la relación pertenece al miembro
    if relacion.miembro_id != miembro.id and relacion.familiar_id != miembro.id:
        messages.error(request, "La relación no pertenece a este miembro.")
        return redirect("miembros_app:familiares_lista", pk=pk)
    
    nombre_familiar = f"{relacion.familiar.nombres} {relacion.familiar.apellidos}"
    relacion.delete()
    
    messages.success(request, f"Se eliminó la relación con {nombre_familiar}.")
    return redirect("miembros_app:familiares_lista", pk=pk)


# ═══════════════════════════════════════════════════════════════════════════════
# VISTAS AJAX
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
def ajax_buscar_miembros(request):
    """Busca miembros para el autocomplete."""
    q = request.GET.get("q", "").strip()
    exclude_id = request.GET.get("exclude", "")
    
    if len(q) < 2:
        return JsonResponse({"results": []})
    
    miembros = Miembro.objects.filter(
        Q(nombres__icontains=q) |
        Q(apellidos__icontains=q) |
        Q(codigo_miembro__icontains=q) |
        Q(codigo_seguimiento__icontains=q)
    )[:15]
    
    if exclude_id:
        miembros = miembros.exclude(pk=exclude_id)
    
    results = []
    for m in miembros:
        results.append({
            "id": m.id,
            "nombre": f"{m.nombres} {m.apellidos}",
            "codigo": m.codigo_miembro or m.codigo_seguimiento or "",
            "foto": m.foto.url if m.foto else None,
        })
    
    return JsonResponse({"results": results})


@login_required
@require_GET
def ajax_validar_relacion(request):
    """Valida una relación familiar antes de guardarla."""
    miembro_id = request.GET.get("miembro_id")
    familiar_id = request.GET.get("familiar_id")
    tipo_relacion = request.GET.get("tipo_relacion")
    relacion_id = request.GET.get("relacion_id")  # Para edición
    
    if not all([miembro_id, familiar_id, tipo_relacion]):
        return JsonResponse({
            "valid": False,
            "errors": ["Faltan parámetros requeridos."],
            "warnings": [],
            "require_confirmation": False,
        }, status=400)
    
    try:
        miembro = Miembro.objects.get(pk=miembro_id)
        familiar = Miembro.objects.get(pk=familiar_id)
    except Miembro.DoesNotExist:
        return JsonResponse({
            "valid": False,
            "errors": ["Miembro no encontrado."],
            "warnings": [],
            "require_confirmation": False,
        }, status=404)
    
    resultado = validar_relacion_familiar(
        miembro=miembro,
        familiar=familiar,
        tipo_relacion=tipo_relacion,
        relacion_id=int(relacion_id) if relacion_id else None,
    )
    
    return JsonResponse({
        "valid": resultado["valid"],
        "errors": resultado["errors"],
        "warnings": resultado["warnings"],
        "require_confirmation": len(resultado["warnings"]) > 0 and resultado["valid"],
    })