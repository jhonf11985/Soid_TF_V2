# -*- coding: utf-8 -*-
"""
miembros_app/views/familiares.py
Vistas y funciones relacionadas con las relaciones familiares.
"""

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db.models import Q

from miembros_app.models import Miembro, MiembroRelacion
from miembros_app.forms import MiembroRelacionForm

from .utils import (
    TIPOS_NUCLEAR,
    TIPOS_ORIGEN,
    TIPOS_EXTENDIDA,
    TIPOS_POLITICA,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES - RELACIONES
# ═══════════════════════════════════════════════════════════════════════════════

def _obtener_relaciones_directas(miembro_id):
    """
    Obtiene todas las relaciones directas de un miembro, normalizadas.
    Retorna: dict con sets de IDs por tipo de relación.
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
    """
    Obtiene TODOS los padres de un miembro (directos + inferidos por cónyuge).
    Retorna: (padres_directos, padres_inferidos)
    """
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
    """
    Obtiene TODOS los hijos de un miembro (directos + inferidos por cónyuge).
    Retorna: (hijos_directos, hijos_inferidos)
    """
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


# ═══════════════════════════════════════════════════════════════════════════════
# CÁLCULO DE PARENTESCOS INFERIDOS
# ═══════════════════════════════════════════════════════════════════════════════

def calcular_parentescos_inferidos(miembro):
    """
    Calcula TODOS los parentescos inferidos de un miembro.
    Usa inferencias en cascada para máxima precisión.
    """
    mi_id = miembro.id
    cache = {}

    # PASO 1: Mis relaciones directas
    mis_rels = _obtener_relaciones_directas(mi_id)
    padres_directos = mis_rels["padres"]
    hijos_directos = mis_rels["hijos"]
    hermanos_directos = mis_rels["hermanos"]
    conyuges_directos = mis_rels["conyuges"]

    # PASO 2: Padres completos
    padres_dir, padres_inf = _obtener_padres_completos(mi_id, cache)
    todos_mis_padres = padres_dir | padres_inf

    # PASO 3: Hijos completos
    hijos_dir, hijos_inf = _obtener_hijos_completos(mi_id, cache)
    todos_mis_hijos = hijos_dir | hijos_inf

    # PASO 4: Hermanos
    hermanos_inferidos = _obtener_hermanos_completos(mi_id, todos_mis_padres)
    hermanos_inferidos |= hermanos_directos
    todos_mis_hermanos = hermanos_inferidos.copy()

    # PASO 5: Abuelos
    abuelos_ids = set()
    for padre_id in todos_mis_padres:
        p_dir, p_inf = _obtener_padres_completos(padre_id, cache)
        abuelos_ids |= p_dir | p_inf

    # PASO 6: Tíos
    tios_ids = set()
    for padre_id in todos_mis_padres:
        p_dir, p_inf = _obtener_padres_completos(padre_id, cache)
        abuelos_linea = p_dir | p_inf
        hermanos_del_padre = _obtener_hermanos_completos(padre_id, abuelos_linea)
        tios_ids |= hermanos_del_padre

    # PASO 7: Sobrinos
    sobrinos_ids = set()
    for hermano_id in todos_mis_hermanos:
        h_dir, h_inf = _obtener_hijos_completos(hermano_id, cache)
        sobrinos_ids |= h_dir | h_inf

    # PASO 8: Primos
    primos_ids = set()
    for tio_id in tios_ids:
        h_dir, h_inf = _obtener_hijos_completos(tio_id, cache)
        primos_ids |= h_dir | h_inf

    # PASO 9: Nietos
    nietos_ids = set()
    for hijo_id in todos_mis_hijos:
        h_dir, h_inf = _obtener_hijos_completos(hijo_id, cache)
        nietos_ids |= h_dir | h_inf

    # PASO 10: Cuñados
    cunados_ids = set()
    for hermano_id in todos_mis_hermanos:
        rels_hermano = _obtener_relaciones_directas(hermano_id)
        cunados_ids |= rels_hermano["conyuges"]
    
    for conyuge_id in conyuges_directos:
        p_dir, p_inf = _obtener_padres_completos(conyuge_id, cache)
        hermanos_conyuge = _obtener_hermanos_completos(conyuge_id, p_dir | p_inf)
        cunados_ids |= hermanos_conyuge

    # PASO 11: Suegros
    suegros_ids = set()
    for conyuge_id in conyuges_directos:
        p_dir, p_inf = _obtener_padres_completos(conyuge_id, cache)
        suegros_ids |= p_dir | p_inf

    # PASO 12: Yernos/Nueras
    yernos_ids = set()
    for hijo_id in todos_mis_hijos:
        rels_hijo = _obtener_relaciones_directas(hijo_id)
        yernos_ids |= rels_hijo["conyuges"]

    # PASO 13: Consuegros
    consuegros_ids = set()
    for yerno_id in yernos_ids:
        p_dir, p_inf = _obtener_padres_completos(yerno_id, cache)
        consuegros_ids |= p_dir | p_inf

    # PASO 14: Bisabuelos
    bisabuelos_ids = set()
    for abuelo_id in abuelos_ids:
        p_dir, p_inf = _obtener_padres_completos(abuelo_id, cache)
        bisabuelos_ids |= p_dir | p_inf

    # PASO 15: Bisnietos
    bisnietos_ids = set()
    for nieto_id in nietos_ids:
        h_dir, h_inf = _obtener_hijos_completos(nieto_id, cache)
        bisnietos_ids |= h_dir | h_inf

    # LIMPIEZA
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

    # CONSTRUIR RESULTADO
    ids_total = set()
    for s in todos_sets:
        ids_total |= s
    
    miembros_map = {
        m.id: m 
        for m in Miembro.objects.filter(id__in=ids_total).only("id", "nombres", "apellidos", "genero")
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
    """
    Obtiene todas las relaciones del miembro organizadas en 4 categorías.
    """
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
        else:
            otro = rel.miembro
            tipo = MiembroRelacion.inverse_tipo(rel.tipo_relacion, rel.miembro.genero)
        
        if otro.id in ids_agregados:
            continue
        ids_agregados.add(otro.id)
        
        dato = {
            "otro": otro,
            "tipo": tipo,
            "tipo_label": MiembroRelacion.label_por_genero(tipo, otro.genero),
            "vive_junto": rel.vive_junto,
            "es_responsable": rel.es_responsable,
            "es_inferida": getattr(rel, 'es_inferida', False),
            "notas": rel.notas,
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


def obtener_familia_completa(miembro):
    """
    Devuelve TODAS las relaciones de un miembro (directas + inferidas).
    """
    mi_id = miembro.id
    
    relaciones_directas = []
    
    rels_qs = (
        MiembroRelacion.objects
        .filter(Q(miembro_id=mi_id) | Q(familiar_id=mi_id))
        .select_related("miembro", "familiar")
    )
    
    for rel in rels_qs:
        if rel.miembro_id == mi_id:
            otro = rel.familiar
            tipo = rel.tipo_relacion
        else:
            otro = rel.miembro
            tipo = MiembroRelacion.inverse_tipo(rel.tipo_relacion, otro.genero)
        
        relaciones_directas.append({
            "otro": otro,
            "tipo": tipo,
            "tipo_label": MiembroRelacion.label_por_genero(tipo, otro.genero),
            "inferido": False,
            "vive_junto": rel.vive_junto,
            "es_responsable": rel.es_responsable,
            "notas": rel.notas,
        })
    
    relaciones_inferidas = calcular_parentescos_inferidos(miembro)
    
    ids_directos = {r["otro"].id for r in relaciones_directas}
    familia_completa = relaciones_directas.copy()
    
    for rel in relaciones_inferidas:
        if rel["otro"].id not in ids_directos:
            familia_completa.append(rel)
    
    return familia_completa


# ═══════════════════════════════════════════════════════════════════════════════
# VISTAS DE FAMILIARES
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
@permission_required("miembros_app.change_miembro", raise_exception=True)
def agregar_familiar(request, pk):
    """Agrega un familiar a un miembro."""
    miembro = get_object_or_404(Miembro, pk=pk)

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
@require_POST
@permission_required("miembros_app.delete_miembrorelacion", raise_exception=True)
def eliminar_familiar(request, relacion_id):
    """Elimina una relación familiar."""
    relacion = get_object_or_404(MiembroRelacion, pk=relacion_id)
    miembro_pk = relacion.miembro.pk

    relacion.delete()
    messages.success(request, "Familiar quitado correctamente.")

    url = reverse("miembros_app:editar", kwargs={"pk": miembro_pk})
    return redirect(f"{url}?tab=familiares")