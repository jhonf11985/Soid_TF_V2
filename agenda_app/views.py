from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    # Placeholder: luego metemos KPIs reales (eventos hoy, semana, pendientes, etc.)
    context = {
        "eventos_hoy": 0,
        "eventos_semana": 0,
        "proximos_eventos": [],
    }
    return render(request, "agenda_app/home.html", context)
