# core/ajax_views.py
# ✅ CON SOPORTE MULTI-TENANT

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
    """
    
    q = request.GET.get("q", "").strip()
    limit = int(request.GET.get("limit", 15))
    filtro = request.GET.get("filtro", "activos")
    
    # Validar límite máximo por seguridad
    limit = min(limit, 50)
    
    # ✅ FILTRAR POR TENANT
    tenant = getattr(request, 'tenant', None)
    if tenant:
        miembros = Miembro.objects.filter(tenant=tenant)
    else:
        miembros = Miembro.objects.none()
    
    # === APLICAR FILTROS ===
    if filtro == "activos":
        miembros = miembros.filter(activo=True)
    elif filtro == "bautizados":
        miembros = miembros.filter(bautizado_confirmado=True, activo=True)
    
    # === BÚSQUEDA POR TÉRMINO ===
    if q:
        miembros = miembros.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(apodo__icontains=q) |
            Q(codigo_miembro__icontains=q) |
            Q(cedula__icontains=q)
        )
    # === ORDENAR Y LIMITAR ===
    miembros = miembros.order_by("nombres", "apellidos")[:limit]
    
    # === CONSTRUIR RESPUESTA JSON ===
    resultados = []
    for miembro in miembros:
        telefono_mostrar = miembro.telefono or miembro.whatsapp or miembro.telefono_secundario or "—"
        
        resultados.append({
            "id": miembro.id,
            "nombre": miembro.nombre_completo,
            "codigo": miembro.codigo_miembro or "—",
            "estado": miembro.get_estado_miembro_display() if miembro.estado_miembro else "—",
            "estado_activo": "✓ Activo" if miembro.activo else "✗ Inactivo",
            "edad": miembro.edad or "—",
            "genero": miembro.get_genero_display() if miembro.genero else "—",
            "telefono": telefono_mostrar,
            "email": miembro.email or "—",
            "cedula": miembro.cedula or "—",
            "bautizado": "✓ Bautizado" if miembro.bautizado_confirmado else "○ Sin bautismo confirmado",
            "es_miembro_oficial": "✓ Oficial" if miembro.es_miembro_oficial else "○ No oficial",
            "texto_mostrado": f"{miembro.nombre_completo} ({miembro.codigo_miembro or 'sin código'})",
        })
    
    return JsonResponse({
        "success": True,
        "resultados": resultados,
        "total": len(resultados),
    }, safe=True)


@login_required
@require_http_methods(["GET"])
def miembro_detalle(request, miembro_id):
    """
    API AJAX para obtener detalles de un miembro específico.
    """
    try:
        # ✅ FILTRAR POR TENANT
        tenant = getattr(request, 'tenant', None)
        if tenant:
            miembro = Miembro.objects.get(id=miembro_id, tenant=tenant)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Tenant no disponible'
            }, status=400)
        
        foto_url = None
        if miembro.foto:
            foto_url = miembro.foto.url
        
        return JsonResponse({
            'success': True,
            'id': miembro.id,
            'nombre': miembro.nombres or '',
            'apellido': miembro.apellidos or '',
            'email': miembro.email or '',
            'foto_url': foto_url,
        })
        
    except Miembro.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Miembro no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    

from django.contrib.auth import get_user_model
User = get_user_model()

@login_required
@require_http_methods(["GET"])
def email_disponible(request):
    email = (request.GET.get("email") or "").strip().lower()
    exclude_id = request.GET.get("exclude_id")

    if not email:
        return JsonResponse({"success": True, "available": True, "message": ""})

    qs = User.objects.filter(email__iexact=email)

    if exclude_id and exclude_id.isdigit():
        qs = qs.exclude(pk=int(exclude_id))

    exists = qs.exists()

    return JsonResponse({
        "success": True,
        "available": not exists,
        "message": "Correo disponible" if not exists else "Ya existe un usuario con este correo."
    })