from django.shortcuts import render, redirect
from django.http import HttpResponse

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
            form.save()
            return redirect("visitas_app:visita_list")
    else:
        form = VisitaForm()

    return render(request, "visitas_app/visita_form.html", {
        "form": form,
    })