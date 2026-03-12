from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest

from .models import Visita
from .forms import VisitaForm


def _get_tenant(request):
    return getattr(request, "tenant", None)


def visita_list(request):
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    visitas = (
        Visita.objects
        .filter(tenant=tenant)
        .select_related("clasificacion")
        .order_by("-fecha_ultima_visita", "-id")
    )

    return render(request, "visitas_app/visita_list.html", {
        "visitas": visitas,
    })


def visita_create(request):
    tenant = _get_tenant(request)
    if tenant is None:
        return HttpResponseBadRequest("No se encontró tenant activo.")

    if request.method == "POST":
        form = VisitaForm(request.POST, tenant=tenant)
        if form.is_valid():
            nombre = (form.cleaned_data.get("nombre") or "").strip()
            telefono = (form.cleaned_data.get("telefono") or "").strip()
            genero = form.cleaned_data.get("genero")
            edad = form.cleaned_data.get("edad")
            clasificacion = form.cleaned_data.get("clasificacion")
            primera_vez_form = form.cleaned_data.get("primera_vez", True)
            invitado_por = form.cleaned_data.get("invitado_por", "")
            desea_contacto = form.cleaned_data.get("desea_contacto", True)
            peticion_oracion = form.cleaned_data.get("peticion_oracion", "")
            hoy = timezone.localdate()

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
                nueva_visita.primera_vez = primera_vez_form
                nueva_visita.fecha_primera_visita = hoy
                nueva_visita.fecha_ultima_visita = hoy
                nueva_visita.cantidad_visitas = 1
                nueva_visita.save()

            return redirect("visitas_app:visita_list")
    else:
        form = VisitaForm(tenant=tenant)

    return render(request, "visitas_app/visita_form.html", {
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