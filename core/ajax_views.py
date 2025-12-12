# core/ajax_views.py

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from miembros_app.models import Miembro


@login_required
@require_http_methods(["GET"])
def buscar_miembros(request):
    """
    API AJAX para buscar miembros activos.
    Búsqueda inteligente en tiempo real con filtros configurables.
    
    Parámetros GET:
    - q: término de búsqueda (nombres, apellidos, código, cédula)
    - limit: máximo de resultados (default 15, máx 50)
    - filtro: 'activos' (default) | 'bautizados' | 'todos'
    
    Responde con JSON:
    {
        "success": true,
        "resultados": [
            {
                "id": 1,
                "nombre": "Juan García",
                "codigo": "TF-0001",
                "estado": "Activo",
                "edad": 35,
                "telefono": "809-555-1234",
                "cedula": "001-1234567-8",
                "texto_mostrado": "Juan García (TF-0001)"
            },
            ...
        ],
        "total": 3
    }
    
    Uso desde AJAX:
        fetch('/api/buscar-miembros/?q=juan&filtro=activos&limit=15')
            .then(r => r.json())
            .then(data => console.log(data.resultados))
    """
    
    q = request.GET.get("q", "").strip()
    limit = int(request.GET.get("limit", 15))
    filtro = request.GET.get("filtro", "activos")
    
    # Validar límite máximo por seguridad
    limit = min(limit, 50)
    
    # Base: todos los miembros
    miembros = Miembro.objects.all()
    
    # === APLICAR FILTROS ===
    if filtro == "activos":
        # Solo miembros activos (no han salido de la iglesia)
        miembros = miembros.filter(activo=True)
    elif filtro == "bautizados":
        # Solo miembros bautizados confirmados y activos
        miembros = miembros.filter(bautizado_confirmado=True, activo=True)
    # 'todos' no aplica filtro adicional (muestra todo el historial)
    
    # === BÚSQUEDA POR TÉRMINO ===
    if q:
        miembros = miembros.filter(
            Q(nombres__icontains=q) |           # Buscar por nombre
            Q(apellidos__icontains=q) |         # Buscar por apellido
            Q(codigo_miembro__icontains=q) |    # Buscar por código (TF-0001)
            Q(cedula__icontains=q)              # Buscar por cédula
        )
    
    # === ORDENAR POR RELEVANCIA ===
    # Primero por nombre, luego por apellido, limitar resultados
    miembros = miembros.order_by("nombres", "apellidos")[:limit]
    
    # === CONSTRUIR RESPUESTA JSON ===
    resultados = []
    for miembro in miembros:
        # Información de contacto prioritaria
        telefono_mostrar = miembro.telefono or miembro.whatsapp or miembro.telefono_secundario or "—"
        
        resultados.append({
            # Campos básicos
            "id": miembro.id,
            "nombre": f"{miembro.nombres} {miembro.apellidos}".strip(),
            "codigo": miembro.codigo_miembro or "—",
            
            # Estado y datos personales
            "estado": miembro.get_estado_miembro_display() if miembro.estado_miembro else "—",
            "estado_activo": "✓ Activo" if miembro.activo else "✗ Inactivo",
            "edad": miembro.edad or "—",
            "genero": miembro.get_genero_display() if miembro.genero else "—",
            
            # Contacto
            "telefono": telefono_mostrar,
            "email": miembro.email or "—",
            "cedula": miembro.cedula or "—",
            
            # Espiritual
            "bautizado": "✓ Bautizado" if miembro.bautizado_confirmado else "○ Sin bautismo confirmado",
            "es_miembro_oficial": "✓ Oficial" if miembro.es_miembro_oficial else "○ No oficial",
            
            # Campo extra para mostrar info resumida en dropdown (simple)
            "texto_mostrado": f"{miembro.nombres} {miembro.apellidos} ({miembro.codigo_miembro or 'sin código'})",
        })
    
    return JsonResponse({
        "success": True,
        "resultados": resultados,
        "total": len(resultados),
    }, safe=True)