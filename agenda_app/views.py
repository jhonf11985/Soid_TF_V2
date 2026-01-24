from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .models import Actividad
from .forms import ActividadForm


MESES_ES = [
    (1, "Enero"),
    (2, "Febrero"),
    (3, "Marzo"),
    (4, "Abril"),
    (5, "Mayo"),
    (6, "Junio"),
    (7, "Julio"),
    (8, "Agosto"),
    (9, "Septiembre"),
    (10, "Octubre"),
    (11, "Noviembre"),
    (12, "Diciembre"),
]


@login_required
def home(request):
    return render(request, "agenda_app/home.html")


@login_required
def agenda_anual(request):
    hoy = date.today()

    year_str = request.GET.get("year")
    try:
        year = int(year_str) if year_str else hoy.year
    except ValueError:
        year = hoy.year

    actividades = (
        Actividad.objects
        .filter(fecha__year=year)
        .order_by("fecha", "hora_inicio", "titulo")
    )

    por_mes = {m: [] for m, _ in MESES_ES}
    for a in actividades:
        por_mes[a.fecha.month].append(a)

    meses_data = []
    for mes_num, mes_nombre in MESES_ES:
        lista = por_mes.get(mes_num, [])
        meses_data.append({
            "mes_num": mes_num,
            "mes_nombre": mes_nombre,
            "total": len(lista),
            "actividades": lista,
        })

    context = {
        "year": year,
        "hoy": hoy,
        "meses_data": meses_data,
    }
    return render(request, "agenda_app/agenda_anual.html", context)


@login_required
def actividad_create(request):
    """
    Crear actividad (V1 simple)
    """
    if request.method == "POST":
        form = ActividadForm(request.POST)
        if form.is_valid():
            actividad = form.save()
            messages.success(request, "✅ Actividad agendada correctamente.")
            # Volvemos a agenda anual del año de la actividad
            return redirect("agenda_app:agenda_anual")
    else:
        form = ActividadForm()

    context = {"form": form}
    return render(request, "agenda_app/actividad_form.html", context)
