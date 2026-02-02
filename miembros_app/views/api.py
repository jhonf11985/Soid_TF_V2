# -*- coding: utf-8 -*-
"""
miembros_app/views/api.py
Vistas que retornan JSON: bloqueo/desbloqueo, validaciones AJAX, links públicos.
"""

from datetime import timedelta
from io import BytesIO

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from django.core.files.base import ContentFile

from miembros_app.models import Miembro
from miembros_app.pdf_reportlab import generar_pdf_listado_miembros_reportlab
from core.models import DocumentoCompartido

from .utils import CEDULA_RE


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def _verificar_admin(request):
    """Verifica si el usuario es admin."""
    return request.user.is_staff or request.user.is_superuser


def _desbloquear_seccion(request, pk, session_key):
    """Lógica común para desbloquear secciones con contraseña."""
    if not _verificar_admin(request):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    
    password = request.POST.get("password", "").strip()
    
    if request.user.check_password(password):
        request.session[f"{session_key}_{pk}"] = True
        return JsonResponse({"ok": True})
    
    return JsonResponse({"ok": False, "error": "Contraseña incorrecta"})


def _bloquear_seccion(request, pk, session_key):
    """Lógica común para bloquear secciones."""
    if not _verificar_admin(request):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    
    request.session.pop(f"{session_key}_{pk}", None)
    return JsonResponse({"ok": True})


# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUEO/DESBLOQUEO DE SECCIONES
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
@permission_required("miembros_app.change_miembro", raise_exception=True)
def miembro_finanzas_desbloquear(request, pk):
    """Desbloquea la sección de finanzas del miembro."""
    return _desbloquear_seccion(request, pk, "miembro_finanzas")


@login_required
@require_POST
@permission_required("miembros_app.change_miembro", raise_exception=True)
def miembro_finanzas_bloquear(request, pk):
    """Bloquea la sección de finanzas del miembro."""
    return _bloquear_seccion(request, pk, "miembro_finanzas")


@login_required
@require_POST
@permission_required("miembros_app.change_miembro", raise_exception=True)
def miembro_privado_desbloquear(request, pk):
    """Desbloquea la sección privada del miembro."""
    return _desbloquear_seccion(request, pk, "miembro_privado")


@login_required
@require_POST
@permission_required("miembros_app.change_miembro", raise_exception=True)
def miembro_privado_bloquear(request, pk):
    """Bloquea la sección privada del miembro."""
    return _bloquear_seccion(request, pk, "miembro_privado")


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDACIÓN DE CÉDULA
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def ajax_validar_cedula(request):
    """
    GET /miembros/ajax/validar-cedula/?cedula=000-0000000-0&pk=123
    Devuelve si la cédula ya existe (excluyendo el pk si viene).
    """
    cedula = (request.GET.get("cedula") or "").strip()
    pk = (request.GET.get("pk") or "").strip()

    if not cedula:
        return JsonResponse({"ok": True, "empty": True, "valid_format": False, "exists": False})

    valid_format = bool(CEDULA_RE.match(cedula))
    if not valid_format:
        return JsonResponse({
            "ok": True,
            "empty": False,
            "valid_format": False,
            "exists": False,
            "message": "Formato inválido. Usa 000-0000000-0",
        })

    qs = Miembro.objects.filter(cedula=cedula)
    if pk.isdigit():
        qs = qs.exclude(pk=int(pk))

    exists = qs.exists()

    return JsonResponse({
        "ok": True,
        "empty": False,
        "valid_format": True,
        "exists": exists,
        "message": "Ya existe un miembro con esta cédula." if exists else "Cédula disponible.",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# LINK PÚBLICO PARA PDF
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.view_miembro", raise_exception=True)
@require_POST
def listado_miembros_crear_link_publico(request):
    """Crea un link público para el listado de miembros en PDF."""
    try:
        miembros = Miembro.objects.filter(activo=True)

        q = request.GET.get("q", "").strip()
        if q:
            miembros = miembros.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(cedula__icontains=q)
            )

        estado = request.GET.get("estado", "")
        if estado:
            miembros = miembros.filter(estado_membresia=estado)

        genero = request.GET.get("genero", "")
        if genero:
            miembros = miembros.filter(genero=genero)

        bautizado = request.GET.get("bautizado", "")
        if bautizado == "1":
            miembros = miembros.filter(bautizado_confirmado=True)
        elif bautizado == "0":
            miembros = miembros.filter(bautizado_confirmado=False)

        filtros = {"q": q, "estado": estado, "genero": genero, "bautizado": bautizado}

        pdf_bytes = generar_pdf_listado_miembros_reportlab(
            miembros=miembros,
            filtros=filtros,
            titulo="Listado de miembros (SOID)",
        )

        doc = DocumentoCompartido(
            titulo="Listado de miembros",
            descripcion="Listado generado desde SOID",
            creado_por=request.user,
            expira_en=timezone.now() + timedelta(days=7),
            activo=True,
        )
        doc.archivo.save("listado_miembros.pdf", ContentFile(pdf_bytes), save=True)

        link_publico = request.build_absolute_uri(reverse("docs:ver", kwargs={"token": doc.token}))

        return JsonResponse({"ok": True, "link": link_publico, "token": doc.token})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"ok": False, "error": str(e)}, status=400)