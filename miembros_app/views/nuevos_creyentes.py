# -*- coding: utf-8 -*-
"""
miembros_app/views/nuevos_creyentes.py
Vistas relacionadas con nuevos creyentes.
"""

from urllib.parse import quote

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q, Count, Exists, OuterRef

from miembros_app.models import Miembro
from miembros_app.forms import NuevoCreyenteForm
from notificaciones_app.utils import crear_notificacion
from nuevo_creyente_app.models import NuevoCreyenteExpediente

from .utils import wa_digits, modulo_nuevo_creyente_activo
from core.utils_config import get_edad_minima_miembro_oficial


# ═══════════════════════════════════════════════════════════════════════════════
# CREAR NUEVO CREYENTE
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.add_miembro", raise_exception=True)
def nuevo_creyente_crear(request):
    """Registro rápido de nuevos creyentes."""
    if request.method == "POST":
        form = NuevoCreyenteForm(request.POST)
        if form.is_valid():
            miembro = form.save()

            try:
                url_detalle = reverse("miembros_app:nuevo_creyente_editar", args=[miembro.pk])
                crear_notificacion(
                    usuario=request.user,
                    titulo="Nuevo creyente registrado",
                    mensaje=f"{miembro.nombres} {miembro.apellidos} ha entregado su vida a Cristo.",
                    url_name=url_detalle,
                    tipo="info",
                )
            except Exception as e:
                print("Error creando notificación:", e)

            messages.success(
                request,
                f"Nuevo creyente registrado correctamente: {miembro.nombres} {miembro.apellidos}."
            )

            # Enviar WhatsApp si se solicitó
            if request.POST.get("enviar_whatsapp") == "1" and miembro.whatsapp:
                mensaje = (
                    f"Hola {miembro.nombres}, 👋\n\n"
                    "¡Bienvenido a Iglesia Torre Fuerte! 🙏\n\n"
                    "Nos alegra mucho que hayas dado este paso tan importante. "
                    "Muy pronto alguien del equipo se pondrá en contacto contigo "
                    "para acompañarte en este nuevo comienzo.\n\n"
                    "Dios te bendiga."
                )
                wa_url = f"https://wa.me/{wa_digits(miembro.whatsapp)}?text={quote(mensaje)}"
                return redirect(wa_url)

            return redirect("miembros_app:nuevo_creyente_lista")
    else:
        form = NuevoCreyenteForm()

    return render(request, "miembros_app/nuevos_creyentes_form.html", {"form": form, "modo": "crear"})


# ═══════════════════════════════════════════════════════════════════════════════
# LISTA DE NUEVOS CREYENTES
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def nuevo_creyente_lista(request):
    """Lista de nuevos creyentes con filtros."""
    query = request.GET.get("q", "").strip()
    genero_filtro = request.GET.get("genero", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()
    solo_contacto = request.GET.get("solo_contacto", "") == "1"
    ver_inactivos = request.GET.get("ver_inactivos", "") == "1"

    miembros = Miembro.objects.filter(nuevo_creyente=True)

    # Por defecto: solo activos
    if not ver_inactivos:
        miembros = miembros.filter(activo=True)

    # Búsqueda
    if query:
        miembros = miembros.filter(
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(telefono__icontains=query) |
            Q(telefono_secundario__icontains=query) |
            Q(email__icontains=query)
        )

    # Filtro por género
    if genero_filtro:
        miembros = miembros.filter(genero=genero_filtro)

    # Filtro por fechas
    if fecha_desde:
        try:
            miembros = miembros.filter(fecha_conversion__gte=fecha_desde)
        except ValueError:
            pass

    if fecha_hasta:
        try:
            miembros = miembros.filter(fecha_conversion__lte=fecha_hasta)
        except ValueError:
            pass

    # Solo con contacto
    if solo_contacto:
        miembros = miembros.filter(
            Q(telefono__isnull=False, telefono__gt="") |
            Q(telefono_secundario__isnull=False, telefono_secundario__gt="") |
            Q(email__isnull=False, email__gt="")
        )

    # Marcar si ya fue enviado al módulo
    miembros = miembros.annotate(
        nc_enviado=Exists(
            NuevoCreyenteExpediente.objects.filter(miembro_id=OuterRef("pk"))
        )
    )

    # Contar padres espirituales
    miembros = miembros.annotate(
        padres_espirituales_count=Count("padres_espirituales", distinct=True)
    )

    miembros = miembros.order_by("-fecha_conversion", "-fecha_creacion", "apellidos", "nombres")

    generos_choices = Miembro._meta.get_field("genero").choices

    context = {
        "miembros": miembros,
        "query": query,
        "genero_filtro": genero_filtro,
        "generos_choices": generos_choices,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "solo_contacto": solo_contacto,
        "hoy": timezone.localdate(),
        "ver_inactivos": ver_inactivos,
    }
    
    return render(request, "miembros_app/nuevos_creyentes_lista.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# EDITAR NUEVO CREYENTE
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
def nuevo_creyente_editar(request, pk):
    """Editar un nuevo creyente."""
    miembro = get_object_or_404(Miembro, pk=pk, nuevo_creyente=True)

    if request.method == "POST":
        form = NuevoCreyenteForm(request.POST, instance=miembro)
        if form.is_valid():
            miembro = form.save()
            messages.success(
                request,
                f"Datos del nuevo creyente actualizados: {miembro.nombres} {miembro.apellidos}."
            )
            return redirect("miembros_app:nuevo_creyente_lista")
    else:
        form = NuevoCreyenteForm(instance=miembro)

    context = {
        "form": form,
        "modo": "editar",
        "miembro": miembro,
    }
    
    return render(request, "miembros_app/nuevos_creyentes_form.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# DETALLE NUEVO CREYENTE
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def nuevo_creyente_detalle(request, pk):
    """Detalle del Nuevo Creyente."""
    miembro = get_object_or_404(Miembro, pk=pk, nuevo_creyente=True)

    edad_minima = get_edad_minima_miembro_oficial()

    # Expediente
    expediente = (
        NuevoCreyenteExpediente.objects
        .filter(miembro=miembro)
        .select_related("responsable")
        .first()
    )
    
    estado_exp = (getattr(expediente, "estado", "") or "").strip().lower()
    expediente_abierto = bool(expediente and estado_exp == "abierto")

    context = {
        "miembro": miembro,
        "expediente": expediente,
        "expediente_abierto": expediente_abierto,
        "EDAD_MINIMA_MIEMBRO_OFICIAL": edad_minima,
        "modulo_nuevo_creyente_activo": modulo_nuevo_creyente_activo(),
    }

    return render(request, "miembros_app/nuevo_creyente_detalle.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# FICHA NUEVO CREYENTE
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.view_miembro", raise_exception=True)
def nuevo_creyente_ficha(request, pk):
    """Ficha imprimible del nuevo creyente."""
    miembro = get_object_or_404(Miembro, pk=pk, nuevo_creyente=True)

    expediente_abierto = NuevoCreyenteExpediente.objects.filter(
        miembro=miembro,
        estado="abierto"
    ).exists()

    context = {
        "miembro": miembro,
        "hoy": timezone.localdate(),
        "puede_dar_salida": not expediente_abierto,
        "expediente_abierto": expediente_abierto,
    }

    return render(request, "miembros_app/reportes/nuevo_creyente_ficha.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# ENVIAR A MÓDULO NUEVO CREYENTE
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
@permission_required("miembros_app.change_miembro", raise_exception=True)
def enviar_a_nuevo_creyente(request, pk):
    """Envía un miembro al módulo de Nuevo Creyente."""
    miembro = get_object_or_404(Miembro, pk=pk)
    next_url = request.POST.get("next") or request.GET.get("next") or reverse("nuevo_creyente_app:dashboard")

    if not miembro.activo:
        messages.error(request, "No se puede enviar a seguimiento: este nuevo creyente ya fue dado de salida.")
        return redirect(next_url)

    if hasattr(miembro, "expediente_nuevo_creyente"):
        messages.info(request, "Este miembro ya fue enviado al módulo de Nuevo Creyente.")
        return redirect(next_url)

    NuevoCreyenteExpediente.objects.create(miembro=miembro, responsable=request.user)

    if not miembro.nuevo_creyente:
        miembro.nuevo_creyente = True
        miembro.save(update_fields=["nuevo_creyente"])

    messages.success(request, "Enviado correctamente al módulo de Nuevo Creyente.")
    return redirect(next_url)