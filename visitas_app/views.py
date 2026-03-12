from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest

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
        .select_related("tipo", "unidad_responsable")
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
        RegistroVisitas.objects.select_related("tipo", "unidad_responsable"),
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
        else:
            nueva_visita = form.save(commit=False)
            nueva_visita.tenant = tenant
            nueva_visita.registro = registro
            nueva_visita.primera_vez = True
            nueva_visita.fecha_primera_visita = hoy
            nueva_visita.fecha_ultima_visita = hoy
            nueva_visita.cantidad_visitas = 1
            nueva_visita.save()

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

def registro_cerrar(request, pk):
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    registro = get_object_or_404(
        RegistroVisitas,
        pk=pk,
        tenant=tenant,
    )

    if request.method == "POST" and registro.estado != "cerrado":
        registro.estado = "cerrado"
        registro.cerrado_at = timezone.now()
        registro.save(update_fields=["estado", "cerrado_at", "updated_at"])

    return redirect("visitas_app:registro_detail", pk=registro.pk)