from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse

from .models import Visita
from .forms import VisitaForm


def visita_list(request):
    visitas = Visita.objects.all()
    return render(request, "visitas_app/visita_list.html", {
        "visitas": visitas,
    })


def visita_create(request):
    if request.method == "POST":
        form = VisitaForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data["nombre"].strip()
            telefono = form.cleaned_data.get("telefono", "").strip()
            tipo = form.cleaned_data["tipo"]
            invitado_por = form.cleaned_data.get("invitado_por", "")
            desea_contacto = form.cleaned_data.get("desea_contacto", True)
            peticion_oracion = form.cleaned_data.get("peticion_oracion", "")
            hoy = timezone.localdate()

            visita_existente = None

            if telefono:
                visita_existente = Visita.objects.filter(telefono=telefono).first()

            if not visita_existente:
                visita_existente = Visita.objects.filter(nombre__iexact=nombre).first()

            if visita_existente:
                visita_existente.nombre = nombre

                if telefono:
                    visita_existente.telefono = telefono

                visita_existente.tipo = tipo
                visita_existente.invitado_por = invitado_por
                visita_existente.desea_contacto = desea_contacto
                visita_existente.peticion_oracion = peticion_oracion
                visita_existente.primera_vez = False
                visita_existente.fecha_ultima_visita = hoy
                visita_existente.cantidad_visitas += 1
                visita_existente.save()
            else:
                nueva_visita = form.save(commit=False)
                nueva_visita.fecha_primera_visita = hoy
                nueva_visita.fecha_ultima_visita = hoy
                nueva_visita.cantidad_visitas = 1
                nueva_visita.save()

            return redirect("visitas_app:visita_list")
    else:
        form = VisitaForm()

    return render(request, "visitas_app/visita_form.html", {
        "form": form,
    })


def visita_buscar_ajax(request):
    nombre = request.GET.get("nombre", "").strip()
    telefono = request.GET.get("telefono", "").strip()

    visita = None

    if telefono:
        visita = Visita.objects.filter(telefono=telefono).first()

    if not visita and nombre:
        visita = Visita.objects.filter(nombre__iexact=nombre).first()

    if visita:
        return JsonResponse({
            "encontrado": True,
            "id": visita.id,
            "nombre": visita.nombre or "",
            "telefono": visita.telefono or "",
            "tipo": visita.tipo or "visita",
            "invitado_por": visita.invitado_por or "",
            "desea_contacto": visita.desea_contacto,
            "peticion_oracion": visita.peticion_oracion or "",
            "primera_vez": visita.primera_vez,
            "cantidad_visitas": visita.cantidad_visitas,
        })

    return JsonResponse({
        "encontrado": False
    })