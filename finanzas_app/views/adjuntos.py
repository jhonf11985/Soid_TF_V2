# finanzas_app/views/adjuntos.py

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse, FileResponse, Http404
from django.core.exceptions import ValidationError
import os

from ..models import MovimientoFinanciero, AdjuntoMovimiento
from ..validators import validar_archivo, validar_tamaño_total


@login_required
@require_POST
@permission_required("finanzas_app.change_movimientofinanciero", raise_exception=True)
def subir_adjunto(request, movimiento_id):
    """
    Sube un archivo adjunto a un movimiento financiero.
    """
    tenant = request.tenant  # 👈 TENANT
    
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    movimiento = get_object_or_404(MovimientoFinanciero, pk=movimiento_id, tenant=tenant)  # 👈 FILTRAR POR TENANT

    if 'archivo' not in request.FILES:
        return JsonResponse({"success": False, "error": "No se recibió ningún archivo"}, status=400)

    archivo = request.FILES['archivo']

    try:
        validar_archivo(archivo)
        validar_tamaño_total(movimiento, archivo.size)

        adjunto = AdjuntoMovimiento.objects.create(
            movimiento=movimiento,
            archivo=archivo,
            nombre_original=archivo.name,
            tamaño=archivo.size,
            tipo_mime=archivo.content_type,
            subido_por=request.user
        )

        return JsonResponse({
            "success": True,
            "adjunto": {
                "id": adjunto.id,
                "nombre": adjunto.nombre_original,
                "tamaño": adjunto.tamaño_formateado(),
                "icono": adjunto.get_icono(),
                "url_descarga": f"/finanzas/adjuntos/{adjunto.id}/descargar/",
                "url_eliminar": f"/finanzas/adjuntos/{adjunto.id}/eliminar/",
                "puede_eliminar": adjunto.puede_eliminar(request.user),
                "es_imagen": adjunto.es_imagen(),
                "url_imagen": adjunto.archivo.url if adjunto.es_imagen() else None,
            }
        })

    except ValidationError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    except Exception as e:
        return JsonResponse({"success": False, "error": f"Error al subir archivo: {str(e)}"}, status=500)


@login_required
@require_POST
@permission_required("finanzas_app.change_movimientofinanciero", raise_exception=True)
def eliminar_adjunto(request, adjunto_id):
    """
    Elimina un adjunto de movimiento.
    """
    tenant = request.tenant  # 👈 TENANT
    
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    adjunto = get_object_or_404(AdjuntoMovimiento, pk=adjunto_id, movimiento__tenant=tenant)  # 👈 FILTRAR POR TENANT

    if not adjunto.puede_eliminar(request.user):
        return JsonResponse({
            "success": False,
            "error": "No tienes permiso para eliminar este archivo"
        }, status=403)

    try:
        nombre = adjunto.nombre_original

        if adjunto.archivo:
            if os.path.isfile(adjunto.archivo.path):
                os.remove(adjunto.archivo.path)

        adjunto.delete()

        return JsonResponse({
            "success": True,
            "mensaje": f"Archivo '{nombre}' eliminado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Error al eliminar archivo: {str(e)}"
        }, status=500)


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def descargar_adjunto(request, adjunto_id):
    """
    Descarga un archivo adjunto.
    """
    tenant = request.tenant  # 👈 TENANT
    adjunto = get_object_or_404(AdjuntoMovimiento, pk=adjunto_id, movimiento__tenant=tenant)  # 👈 FILTRAR POR TENANT

    if not adjunto.archivo:
        raise Http404("Archivo no encontrado")

    try:
        archivo = open(adjunto.archivo.path, 'rb')
        response = FileResponse(archivo)

        response['Content-Type'] = adjunto.tipo_mime or 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{adjunto.nombre_original}"'
        response['Content-Length'] = adjunto.tamaño

        return response

    except FileNotFoundError:
        raise Http404("Archivo no encontrado en el servidor")
    except Exception as e:
        raise Http404(f"Error al descargar archivo: {str(e)}")


@login_required
@require_GET
@permission_required("finanzas_app.view_movimientofinanciero", raise_exception=True)
def listar_adjuntos(request, movimiento_id):
    """
    Lista todos los adjuntos de un movimiento (JSON para AJAX).
    """
    tenant = request.tenant  # 👈 TENANT
    movimiento = get_object_or_404(MovimientoFinanciero, pk=movimiento_id, tenant=tenant)  # 👈 FILTRAR POR TENANT

    adjuntos = AdjuntoMovimiento.objects.filter(movimiento=movimiento)

    data = {
        "success": True,
        "adjuntos": [
            {
                "id": adj.id,
                "nombre": adj.nombre_original,
                "tamaño": adj.tamaño_formateado(),
                "icono": adj.get_icono(),
                "url_descarga": f"/finanzas/adjuntos/{adj.id}/descargar/",
                "url_eliminar": f"/finanzas/adjuntos/{adj.id}/eliminar/",
                "puede_eliminar": adj.puede_eliminar(request.user),
                "es_imagen": adj.es_imagen(),
                "url_imagen": adj.archivo.url if adj.es_imagen() else None,
                "subido_por": adj.subido_por.get_full_name() if adj.subido_por else "Sistema",
                "subido_en": adj.subido_en.strftime("%d/%m/%Y %H:%M"),
            }
            for adj in adjuntos
        ]
    }

    return JsonResponse(data)