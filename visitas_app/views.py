from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Visita, RegistroVisitas
from .forms import VisitaForm, RegistroVisitasForm


def _get_tenant(request):
    return getattr(request, "tenant", None)


def registro_list(request):
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    registros = (
        RegistroVisitas.objects
        .filter(tenant=tenant)
        .select_related("tipo", "unidad_responsable", "cerrado_por")
        .order_by("-fecha", "-id")
    )

    return render(request, "visitas_app/registro_list.html", {
        "registros": registros,
    })


def registro_create(request):
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    if request.method == "POST":
        form = RegistroVisitasForm(request.POST, tenant=tenant)
        if form.is_valid():
            registro = form.save(commit=False)
            registro.tenant = tenant
            registro.save()
            messages.success(request, "Registro creado exitosamente.")
            return redirect("visitas_app:registro_detail", pk=registro.pk)
    else:
        form = RegistroVisitasForm(tenant=tenant)

    return render(request, "visitas_app/registro_form.html", {
        "form": form,
    })


def registro_detail(request, pk):
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    registro = get_object_or_404(
        RegistroVisitas.objects.select_related(
            "tipo", "unidad_responsable", "cerrado_por", "reabierto_por"
        ),
        pk=pk,
        tenant=tenant,
    )

    visitas = (
        registro.visitas
        .select_related("clasificacion")
        .order_by("-created_at", "-id")
    )

    form = VisitaForm(tenant=tenant)

    return render(request, "visitas_app/registro_detail.html", {
        "registro": registro,
        "visitas": visitas,
        "form": form,
    })


def visita_create_en_registro(request, registro_id):
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    registro = get_object_or_404(
        RegistroVisitas,
        pk=registro_id,
        tenant=tenant,
    )

    if registro.estado == "cerrado":
        messages.warning(request, "No se pueden agregar visitas a un registro cerrado.")
        return redirect("visitas_app:registro_detail", pk=registro.pk)

    if request.method != "POST":
        return redirect("visitas_app:registro_detail", pk=registro.pk)

    form = VisitaForm(request.POST, tenant=tenant)
    if form.is_valid():
        nombre = (form.cleaned_data.get("nombre") or "").strip()
        telefono = (form.cleaned_data.get("telefono") or "").strip()
        genero = form.cleaned_data.get("genero")
        edad = form.cleaned_data.get("edad")
        clasificacion = form.cleaned_data.get("clasificacion")
        invitado_por = form.cleaned_data.get("invitado_por", "")
        desea_contacto = form.cleaned_data.get("desea_contacto", True)
        peticion_oracion = form.cleaned_data.get("peticion_oracion", "")
        hoy = registro.fecha or timezone.localdate()

        visita_existente = None

        if telefono:
            visita_existente = Visita.objects.filter(
                tenant=tenant,
                telefono=telefono
            ).first()

        if not visita_existente and nombre:
            visita_existente = Visita.objects.filter(
                tenant=tenant,
                nombre__iexact=nombre
            ).first()

        if visita_existente:
            visita_existente.registro = registro
            visita_existente.nombre = nombre

            if telefono:
                visita_existente.telefono = telefono

            visita_existente.genero = genero
            visita_existente.edad = edad
            visita_existente.clasificacion = clasificacion
            visita_existente.invitado_por = invitado_por
            visita_existente.desea_contacto = desea_contacto
            visita_existente.peticion_oracion = peticion_oracion
            visita_existente.primera_vez = False
            visita_existente.fecha_ultima_visita = hoy
            visita_existente.cantidad_visitas = (visita_existente.cantidad_visitas or 0) + 1
            visita_existente.save()
            messages.info(request, f"Visita actualizada: {nombre} (visita #{visita_existente.cantidad_visitas})")
        else:
            nueva_visita = form.save(commit=False)
            nueva_visita.tenant = tenant
            nueva_visita.registro = registro
            nueva_visita.primera_vez = True
            nueva_visita.fecha_primera_visita = hoy
            nueva_visita.fecha_ultima_visita = hoy
            nueva_visita.cantidad_visitas = 1
            nueva_visita.save()
            messages.success(request, f"Nueva visita registrada: {nombre}")

        return redirect("visitas_app:registro_detail", pk=registro.pk)

    visitas = (
        registro.visitas
        .select_related("clasificacion")
        .order_by("-created_at", "-id")
    )

    return render(request, "visitas_app/registro_detail.html", {
        "registro": registro,
        "visitas": visitas,
        "form": form,
    })


def visita_buscar_ajax(request):
    tenant = _get_tenant(request)
    if tenant is None:
        return JsonResponse({
            "encontrado": False,
            "error": "No se encontró tenant activo."
        }, status=400)

    nombre = (request.GET.get("nombre") or "").strip()
    telefono = (request.GET.get("telefono") or "").strip()

    visita = None

    if telefono:
        visita = (
            Visita.objects
            .filter(tenant=tenant, telefono=telefono)
            .select_related("clasificacion")
            .first()
        )

    if not visita and nombre:
        visita = (
            Visita.objects
            .filter(tenant=tenant, nombre__iexact=nombre)
            .select_related("clasificacion")
            .first()
        )

    if visita:
        return JsonResponse({
            "encontrado": True,
            "id": visita.id,
            "nombre": visita.nombre or "",
            "telefono": visita.telefono or "",
            "genero": visita.genero or "",
            "edad": visita.edad,
            "clasificacion": visita.clasificacion_id if visita.clasificacion else "",
            "clasificacion_nombre": visita.clasificacion.nombre if visita.clasificacion else "",
            "invitado_por": visita.invitado_por or "",
            "desea_contacto": visita.desea_contacto,
            "peticion_oracion": visita.peticion_oracion or "",
            "primera_vez": visita.primera_vez,
            "cantidad_visitas": visita.cantidad_visitas or 0,
        })

    return JsonResponse({
        "encontrado": False
    })


@login_required
def registro_cerrar(request, pk):
    """Cierra un registro de visitas con auditoría."""
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    registro = get_object_or_404(
        RegistroVisitas,
        pk=pk,
        tenant=tenant,
    )

    if request.method == "POST" and registro.estado != "cerrado":
        registro.cerrar(usuario=request.user)
        messages.success(
            request,
            f"Registro cerrado exitosamente por {request.user.get_full_name() or request.user.username}."
        )

    return redirect("visitas_app:registro_detail", pk=registro.pk)


@login_required
def registro_reabrir(request, pk):
    """Reabre un registro de visitas cerrado."""
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    registro = get_object_or_404(
        RegistroVisitas,
        pk=pk,
        tenant=tenant,
    )

    if request.method == "POST" and registro.estado == "cerrado":
        # Verificar que no haya otro registro abierto del mismo tipo
        existe_abierto = RegistroVisitas.objects.filter(
            tenant=tenant,
            tipo=registro.tipo,
            estado="abierto",
        ).exclude(pk=registro.pk).exists()

        if existe_abierto:
            messages.error(
                request,
                f'No se puede reabrir. Ya existe otro registro abierto para "{registro.tipo.nombre}".'
            )
        else:
            registro.reabrir(usuario=request.user)
            messages.success(
                request,
                f"Registro reabierto exitosamente por {request.user.get_full_name() or request.user.username}."
            )

    return redirect("visitas_app:registro_detail", pk=registro.pk)

from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponse
from django.utils import timezone
from datetime import datetime

from .models import Visita, RegistroVisitas, TipoRegistroVisita, ClasificacionVisita

# Para PDF
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER


def _get_tenant(request):
    return getattr(request, "tenant", None)


def _parse_date(date_str):
    """Parsea una fecha en formato YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def reporte_visitas(request):
    """Vista principal del reporte de visitas con filtros."""
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    # Obtener parámetros de filtro
    fecha_desde = request.GET.get("fecha_desde", "")
    fecha_hasta = request.GET.get("fecha_hasta", "")
    tipo_id = request.GET.get("tipo", "")
    clasificacion_id = request.GET.get("clasificacion", "")
    primera_vez = request.GET.get("primera_vez", "")

    # Base queryset
    visitas = (
        Visita.objects
        .filter(tenant=tenant)
        .select_related("registro", "registro__tipo", "clasificacion")
        .order_by("-fecha_ultima_visita", "-id")
    )

    # Aplicar filtros
    fecha_desde_parsed = _parse_date(fecha_desde)
    fecha_hasta_parsed = _parse_date(fecha_hasta)

    if fecha_desde_parsed:
        visitas = visitas.filter(fecha_ultima_visita__gte=fecha_desde_parsed)
    
    if fecha_hasta_parsed:
        visitas = visitas.filter(fecha_ultima_visita__lte=fecha_hasta_parsed)

    if tipo_id:
        visitas = visitas.filter(registro__tipo_id=tipo_id)

    if clasificacion_id:
        visitas = visitas.filter(clasificacion_id=clasificacion_id)

    if primera_vez == "si":
        visitas = visitas.filter(primera_vez=True)
    elif primera_vez == "no":
        visitas = visitas.filter(primera_vez=False)

    # Calcular resumen
    total_visitas = visitas.count()
    total_primera_vez = visitas.filter(primera_vez=True).count()
    total_recurrentes = total_visitas - total_primera_vez

    # Obtener opciones para filtros
    tipos = TipoRegistroVisita.objects.filter(tenant=tenant, activo=True).order_by("orden", "nombre")
    clasificaciones = ClasificacionVisita.objects.filter(tenant=tenant, activo=True).order_by("orden", "nombre")

    # Verificar si hay filtros activos
    filtros_activos = any([fecha_desde, fecha_hasta, tipo_id, clasificacion_id, primera_vez])

    context = {
        "visitas": visitas,
        "total_visitas": total_visitas,
        "total_primera_vez": total_primera_vez,
        "total_recurrentes": total_recurrentes,
        "tipos": tipos,
        "clasificaciones": clasificaciones,
        # Valores actuales de filtros
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "tipo_id": tipo_id,
        "clasificacion_id": clasificacion_id,
        "primera_vez": primera_vez,
        "filtros_activos": filtros_activos,
    }

    return render(request, "visitas_app/reporte_visitas.html", context)


def reporte_visitas_pdf(request):
    """Genera PDF del reporte de visitas con los filtros aplicados."""
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    # Obtener parámetros de filtro (mismos que la vista principal)
    fecha_desde = request.GET.get("fecha_desde", "")
    fecha_hasta = request.GET.get("fecha_hasta", "")
    tipo_id = request.GET.get("tipo", "")
    clasificacion_id = request.GET.get("clasificacion", "")
    primera_vez = request.GET.get("primera_vez", "")

    # Base queryset
    visitas = (
        Visita.objects
        .filter(tenant=tenant)
        .select_related("registro", "registro__tipo", "clasificacion")
        .order_by("-fecha_ultima_visita", "-id")
    )

    # Aplicar filtros
    fecha_desde_parsed = _parse_date(fecha_desde)
    fecha_hasta_parsed = _parse_date(fecha_hasta)

    if fecha_desde_parsed:
        visitas = visitas.filter(fecha_ultima_visita__gte=fecha_desde_parsed)
    
    if fecha_hasta_parsed:
        visitas = visitas.filter(fecha_ultima_visita__lte=fecha_hasta_parsed)

    if tipo_id:
        visitas = visitas.filter(registro__tipo_id=tipo_id)

    if clasificacion_id:
        visitas = visitas.filter(clasificacion_id=clasificacion_id)

    if primera_vez == "si":
        visitas = visitas.filter(primera_vez=True)
    elif primera_vez == "no":
        visitas = visitas.filter(primera_vez=False)

    # Calcular resumen
    total_visitas = visitas.count()
    total_primera_vez = visitas.filter(primera_vez=True).count()
    total_recurrentes = total_visitas - total_primera_vez

    # Crear PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
    )

    elements = []
    styles = getSampleStyleSheet()

    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0097A7'),
        spaceAfter=6,
        alignment=TA_CENTER,
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6C757D'),
        spaceAfter=20,
        alignment=TA_CENTER,
    )

    # Encabezado
    elements.append(Paragraph(tenant.nombre if hasattr(tenant, 'nombre') else "Iglesia", title_style))
    
    # Subtítulo con rango de fechas
    fecha_texto = "Reporte de Visitas"
    if fecha_desde_parsed and fecha_hasta_parsed:
        fecha_texto += f" - {fecha_desde_parsed.strftime('%d/%m/%Y')} al {fecha_hasta_parsed.strftime('%d/%m/%Y')}"
    elif fecha_desde_parsed:
        fecha_texto += f" - Desde {fecha_desde_parsed.strftime('%d/%m/%Y')}"
    elif fecha_hasta_parsed:
        fecha_texto += f" - Hasta {fecha_hasta_parsed.strftime('%d/%m/%Y')}"
    else:
        fecha_texto += f" - Generado: {timezone.localdate().strftime('%d/%m/%Y')}"
    
    elements.append(Paragraph(fecha_texto, subtitle_style))

    # Resumen
    resumen_data = [
        ["Total Visitas", "Primera Vez", "Recurrentes"],
        [str(total_visitas), str(total_primera_vez), str(total_recurrentes)],
    ]

    resumen_table = Table(resumen_data, colWidths=[2*inch, 2*inch, 2*inch])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0097A7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, 1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#E0F7FA')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0097A7')),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 20))

    # Tabla de visitas
    if visitas.exists():
        # Encabezados
        data = [["Nombre", "Teléfono", "Fecha", "Tipo", "Clasificación", "Género", "Edad", "Visitas", "1ra vez"]]

        for v in visitas[:500]:  # Limitar a 500 para rendimiento
            data.append([
                v.nombre or "-",
                v.telefono or "-",
                v.fecha_ultima_visita.strftime('%d/%m/%Y') if v.fecha_ultima_visita else "-",
                v.registro.tipo.nombre if v.registro and v.registro.tipo else "-",
                v.clasificacion.nombre if v.clasificacion else "-",
                v.get_genero_display() if v.genero else "-",
                str(v.edad) if v.edad else "-",
                str(v.cantidad_visitas or 1),
                "Sí" if v.primera_vez else "No",
            ])

        col_widths = [1.8*inch, 1.1*inch, 0.85*inch, 1.3*inch, 1.2*inch, 0.7*inch, 0.5*inch, 0.6*inch, 0.65*inch]
        
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0097A7')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            # Cuerpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),  # Fecha
            ('ALIGN', (5, 0), (-1, -1), 'CENTER'),  # Género, Edad, Visitas, 1ra vez
            # Líneas
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#00838F')),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#DEE2E6')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#DEE2E6')),
            # Filas alternas
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        ]))
        elements.append(table)

        if visitas.count() > 500:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(
                f"Mostrando 500 de {visitas.count()} registros. Ajuste los filtros para ver datos específicos.",
                ParagraphStyle('Note', fontSize=8, textColor=colors.HexColor('#6C757D'), alignment=TA_CENTER)
            ))
    else:
        elements.append(Paragraph(
            "No se encontraron visitas con los filtros seleccionados.",
            ParagraphStyle('NoData', fontSize=12, textColor=colors.HexColor('#6C757D'), alignment=TA_CENTER)
        ))

    doc.build(elements)
    buffer.seek(0)

    # Nombre del archivo
    filename = f"reporte_visitas_{timezone.localdate().strftime('%Y%m%d')}.pdf"

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response