# miembros_app/views_reportes.py
# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES NUEVAS PARA COMPARTIR POR WHATSAPP
# (Sin generación de PDF del servidor)
# ═══════════════════════════════════════════════════════════════════════════════

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.urls import reverse
from urllib.parse import quote

from .models import Miembro


@login_required
@permission_required("miembros_app.view_miembro", raise_exception=True)
def compartir_listado_whatsapp(request):
    """
    Devuelve un JSON con la URL de WhatsApp para compartir el listado.
    El usuario debe guardar el PDF manualmente desde el navegador y adjuntarlo.
    
    FLUJO:
    1. Usuario hace clic en "Compartir por WhatsApp"
    2. Se abre WhatsApp con un mensaje prellenado que incluye el enlace
    3. El destinatario abre el enlace y puede guardar como PDF (Ctrl+P)
    """
    # URL del reporte imprimible (con los mismos filtros)
    filtros = request.GET.urlencode()
    reporte_url = request.build_absolute_uri(
        reverse("miembros_app:reporte_listado_miembros")
    )
    if filtros:
        reporte_url += f"?{filtros}"
    
    # Mensaje prellenado
    mensaje = (
        "📋 *Listado de Miembros*\n\n"
        "Te comparto el listado de miembros.\n\n"
        f"🔗 Ver en línea: {reporte_url}\n\n"
        "_Para obtener el PDF: abre el enlace → Ctrl+P → Guardar como PDF_"
    )
    
    wa_url = f"https://wa.me/?text={quote(mensaje)}"
    
    return JsonResponse({
        "ok": True,
        "wa_url": wa_url,
        "reporte_url": reporte_url,
    })


@login_required
@permission_required("miembros_app.view_miembro", raise_exception=True)
def compartir_ficha_whatsapp(request, pk):
    """
    Devuelve un JSON con la URL de WhatsApp para compartir la ficha de un miembro.
    """
    miembro = get_object_or_404(Miembro, pk=pk)
    
    # URL de la ficha imprimible
    ficha_url = request.build_absolute_uri(
        reverse("miembros_app:ficha", args=[pk])
    )
    
    mensaje = (
        f"📋 *Ficha de {miembro.nombres} {miembro.apellidos}*\n\n"
        f"🔗 Ver ficha: {ficha_url}\n\n"
        "_Para obtener el PDF: abre el enlace → Ctrl+P → Guardar como PDF_"
    )
    
    wa_url = f"https://wa.me/?text={quote(mensaje)}"
    
    return JsonResponse({
        "ok": True,
        "wa_url": wa_url,
        "ficha_url": ficha_url,
        "miembro": f"{miembro.nombres} {miembro.apellidos}",
    })


@login_required
@permission_required("miembros_app.view_miembro", raise_exception=True)
def compartir_nuevos_creyentes_whatsapp(request):
    """
    Devuelve un JSON con la URL de WhatsApp para compartir el listado de nuevos creyentes.
    """
    # URL del reporte imprimible (con los mismos filtros)
    filtros = request.GET.urlencode()
    reporte_url = request.build_absolute_uri(
        reverse("miembros_app:reporte_nuevos_creyentes")
    )
    if filtros:
        reporte_url += f"?{filtros}"
    
    mensaje = (
        "📋 *Listado de Nuevos Creyentes*\n\n"
        "Te comparto el listado de nuevos creyentes.\n\n"
        f"🔗 Ver en línea: {reporte_url}\n\n"
        "_Para obtener el PDF: abre el enlace → Ctrl+P → Guardar como PDF_"
    )
    
    wa_url = f"https://wa.me/?text={quote(mensaje)}"
    
    return JsonResponse({
        "ok": True,
        "wa_url": wa_url,
        "reporte_url": reporte_url,
    })