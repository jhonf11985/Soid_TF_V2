# -*- coding: utf-8 -*-
"""
miembros_app/views/extras.py
Vistas adicionales: mapa, bitácora, padres espirituales, validación teléfono, envío de emails.
"""

import re

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse
from django.db.models import Count
from django.conf import settings

from miembros_app.models import Miembro, MiembroBitacora, ZonaGeo
from miembros_app.forms import EnviarFichaMiembroEmailForm
from core.models import ConfiguracionSistema
from core.utils_email import enviar_correo_sistema


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDACIÓN DE TELÉFONO
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def validar_telefono(request):
    """Valida si un teléfono ya existe en la base de datos."""
    telefono = request.GET.get("telefono", "")
    pk = request.GET.get("pk", "")

    # Normalizar: solo dígitos, quitar el 1 inicial si tiene 11
    telefono_norm = re.sub(r"\D+", "", telefono)
    if len(telefono_norm) == 11 and telefono_norm.startswith("1"):
        telefono_norm = telefono_norm[1:]
    telefono_norm = telefono_norm[:10]

    if not telefono_norm:
        return JsonResponse({"existe": False})

    qs = Miembro.objects.filter(telefono_norm=telefono_norm)

    if pk:
        qs = qs.exclude(pk=pk)

    return JsonResponse({"existe": qs.exists()})


# ═══════════════════════════════════════════════════════════════════════════════
# MAPA DE MIEMBROS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.view_miembro", raise_exception=True)
def mapa_miembros(request):
    """Pantalla del mapa (Leaflet). Los puntos se cargan por AJAX desde la API."""
    return render(request, "miembros_app/mapa_miembros.html")


@login_required
@require_GET
@permission_required("miembros_app.view_miembro", raise_exception=True)
def api_mapa_miembros(request):
    """
    Devuelve puntos por zona (sector/ciudad/provincia) con conteo,
    usando ZonaGeo como cache de coordenadas.
    """
    activo = request.GET.get("activo", "")
    tipo = request.GET.get("tipo", "")
    estado = request.GET.get("estado", "")

    qs = Miembro.objects.all()

    if activo == "1":
        qs = qs.filter(activo=True)
    elif activo == "0":
        qs = qs.filter(activo=False)

    if tipo == "miembro":
        qs = qs.filter(nuevo_creyente=False)
    elif tipo == "nuevo":
        qs = qs.filter(nuevo_creyente=True)

    if estado:
        qs = qs.filter(estado_miembro=estado)

    agrupado = (
        qs.values("sector", "ciudad", "provincia")
          .annotate(total=Count("id"))
          .order_by("-total")
    )

    puntos = []
    faltantes = []

    for row in agrupado:
        sector = (row.get("sector") or "").strip()
        ciudad = (row.get("ciudad") or "").strip()
        provincia = (row.get("provincia") or "").strip()
        total = row["total"]

        zona = ZonaGeo.objects.filter(
            sector=sector,
            ciudad=ciudad,
            provincia=provincia,
        ).first()

        if zona and zona.lat is not None and zona.lng is not None:
            puntos.append({
                "sector": sector,
                "ciudad": ciudad,
                "provincia": provincia,
                "total": total,
                "lat": zona.lat,
                "lng": zona.lng,
            })
        else:
            faltantes.append({
                "sector": sector,
                "ciudad": ciudad,
                "provincia": provincia,
                "total": total,
            })

    return JsonResponse({
        "puntos": puntos,
        "faltantes": faltantes[:50],
        "faltantes_total": len(faltantes),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# BITÁCORA DEL MIEMBRO
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
@permission_required("miembros_app.change_miembro", raise_exception=True)
def miembro_bitacora_add(request, pk):
    """Agregar una entrada manual a la bitácora del miembro."""
    miembro = get_object_or_404(Miembro, pk=pk)
    
    tipo = request.POST.get("tipo", "sistema")
    texto = request.POST.get("texto", "").strip()
    
    if texto:
        titulo = "Nota registrada" if tipo == "nota" else "Mensaje"
        
        MiembroBitacora.objects.create(
            miembro=miembro,
            tipo=tipo,
            titulo=titulo,
            detalle=texto,
            creado_por=request.user,
        )
        
        messages.success(request, "Entrada agregada a la bitácora.")
    else:
        messages.error(request, "El texto no puede estar vacío.")
    
    return redirect("miembros_app:detalle", pk=miembro.pk)


# ═══════════════════════════════════════════════════════════════════════════════
# PADRES ESPIRITUALES
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
@require_POST
def padre_espiritual_add_simple(request, miembro_id):
    """Asigna un padre espiritual a un miembro."""
    miembro = get_object_or_404(Miembro, pk=miembro_id)
    return_url = request.POST.get(
        "return_to",
        reverse("miembros_app:nuevo_creyente_detalle", kwargs={"pk": miembro.pk})
    )

    padre_id = request.POST.get("padre_espiritual_id")
    if not padre_id:
        messages.error(request, "Debes seleccionar un padre espiritual.")
        return redirect(return_url)

    padre = get_object_or_404(Miembro, pk=int(padre_id))

    if padre == miembro:
        messages.error(request, "Un miembro no puede ser su propio padre espiritual.")
        return redirect(return_url)

    miembro.padres_espirituales.add(padre)
    messages.success(request, f"Padre espiritual asignado: {padre.nombres} {padre.apellidos}.")

    return redirect(return_url)


@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
@require_POST
def padre_espiritual_remove_simple(request, miembro_id, padre_id):
    """Remueve un padre espiritual de un miembro."""
    miembro = get_object_or_404(Miembro, pk=miembro_id)
    padre = get_object_or_404(Miembro, pk=padre_id)

    miembro.padres_espirituales.remove(padre)
    messages.success(request, f"Padre espiritual removido: {padre.nombres} {padre.apellidos}.")

    return redirect(
        request.POST.get(
            "return_to",
            reverse("miembros_app:nuevo_creyente_detalle", kwargs={"pk": miembro.pk})
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENVÍO DE FICHAS POR EMAIL
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required("miembros_app.change_miembro", raise_exception=True)
def miembro_enviar_ficha_email(request, pk):
    """Envía la ficha de un miembro por correo electrónico."""
    from .utils import generar_pdf_desde_html
    from django.template.loader import render_to_string
    
    miembro = get_object_or_404(Miembro, pk=pk)
    config = ConfiguracionSistema.load()

    nombre_adjunto_auto = f"ficha_miembro_{miembro.pk}.pdf"

    destinatario_inicial = miembro.email or config.email_oficial or settings.DEFAULT_FROM_EMAIL
    asunto_inicial = f"Ficha del miembro: {miembro.nombres} {miembro.apellidos}"
    mensaje_inicial = (
        f"Le enviamos la ficha del miembro {miembro.nombres} {miembro.apellidos} "
        f"de la iglesia {config.nombre_iglesia or 'Torre Fuerte'}."
    )

    if request.method == "POST":
        form = EnviarFichaMiembroEmailForm(request.POST)
        if form.is_valid():
            destinatario = form.cleaned_data["destinatario"]
            asunto = form.cleaned_data["asunto"] or asunto_inicial
            mensaje = form.cleaned_data["mensaje"] or mensaje_inicial

            try:
                # Generar PDF
                html_string = render_to_string(
                    "miembros_app/reportes/miembro_ficha.html",
                    {"miembro": miembro, "CFG": config},
                    request=request
                )
                pdf_bytes = generar_pdf_desde_html(html_string)

                body_html = (
                    f"<p>{mensaje}</p>"
                    "<p style='margin-top:16px;'>Bendiciones,<br><strong>Soid_Tf_2</strong></p>"
                )

                enviar_correo_sistema(
                    subject=asunto,
                    heading="Ficha de miembro",
                    subheading=f"{miembro.nombres} {miembro.apellidos}",
                    body_html=body_html,
                    destinatarios=destinatario,
                    meta_text="Correo enviado desde el sistema Soid_Tf_2.",
                    extra_context={"CFG": config},
                    adjuntos=[(nombre_adjunto_auto, pdf_bytes)],
                )

                messages.success(request, f"Correo enviado correctamente a {destinatario}.")
                return redirect("miembros_app:detalle", pk=miembro.pk)

            except Exception as e:
                messages.error(request, f"No se pudo enviar el correo: {e}")

    else:
        form = EnviarFichaMiembroEmailForm(
            initial={
                "destinatario": destinatario_inicial,
                "asunto": asunto_inicial,
                "mensaje": mensaje_inicial,
            }
        )

    context = {
        "form": form,
        "miembro": miembro,
        "titulo_pagina": "Enviar ficha por correo",
        "descripcion": "Completa los datos para enviar esta ficha por correo electrónico.",
        "objeto_label": f"Miembro: {miembro.nombres} {miembro.apellidos}",
        "url_cancelar": reverse("miembros_app:detalle", args=[miembro.pk]),
        "adjunto_auto_nombre": nombre_adjunto_auto,
    }
    return render(request, "core/enviar_email.html", context)


@login_required
@permission_required("miembros_app.view_miembro", raise_exception=True)
def nuevos_creyentes_enviar_email(request):
    """Genera un PDF del listado de nuevos creyentes y lo envía por correo."""
    from .utils import generar_pdf_desde_html
    from django.template.loader import render_to_string
    
    config = ConfiguracionSistema.load()

    email_default = config.email_oficial or settings.DEFAULT_FROM_EMAIL
    asunto_default = "Listado de nuevos creyentes"
    mensaje_default = f"Adjunto el listado de nuevos creyentes de {config.nombre_iglesia or 'nuestra iglesia'}."

    if request.method == "POST":
        form = EnviarFichaMiembroEmailForm(request.POST)
        if form.is_valid():
            destinatario = form.cleaned_data["destinatario"]
            asunto = form.cleaned_data["asunto"] or asunto_default
            mensaje = form.cleaned_data["mensaje"] or mensaje_default

            try:
                miembros = Miembro.objects.filter(nuevo_creyente=True, activo=True)
                
                html_string = render_to_string(
                    "miembros_app/reportes/reporte_nuevos_creyentes.html",
                    {"miembros": miembros, "CFG": config},
                    request=request
                )
                pdf_bytes = generar_pdf_desde_html(html_string)

                body_html = (
                    f"<p>{mensaje}</p>"
                    "<p style='margin-top:16px;'>Bendiciones,<br><strong>Soid_Tf_2</strong></p>"
                )

                enviar_correo_sistema(
                    subject=asunto,
                    heading="Listado de nuevos creyentes",
                    body_html=body_html,
                    destinatarios=destinatario,
                    meta_text="Correo enviado desde Soid_Tf_2",
                    extra_context={"CFG": config},
                    adjuntos=[("nuevos_creyentes.pdf", pdf_bytes)],
                )

                messages.success(request, f"Correo enviado correctamente a {destinatario}.")
                return redirect("miembros_app:nuevo_creyente_lista")

            except Exception as e:
                messages.error(request, f"No se pudo enviar el correo: {e}")
                return redirect("miembros_app:nuevo_creyente_lista")
    else:
        form = EnviarFichaMiembroEmailForm(
            initial={
                "destinatario": email_default,
                "asunto": asunto_default,
                "mensaje": mensaje_default,
            }
        )

    return render(
        request,
        "core/enviar_email.html",
        {
            "form": form,
            "titulo_pagina": "Enviar listado de nuevos creyentes",
            "descripcion": "Se generará un PDF del listado.",
            "objeto_label": "Listado de nuevos creyentes",
            "url_cancelar": reverse("miembros_app:nuevo_creyente_lista"),
            "adjunto_auto_nombre": "nuevos_creyentes.pdf",
        },
    )