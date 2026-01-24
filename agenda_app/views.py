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

    # ==========================================================
    # SOLO FUTURAS:
    # - Si el año es el actual: fecha >= hoy
    # - Si el año es futuro: todas (porque todas son futuras)
    # - Si el año es pasado: ninguna
    # ==========================================================
    qs = Actividad.objects.all()

    if year < hoy.year:
        actividades = Actividad.objects.none()
    elif year == hoy.year:
        actividades = (
            qs.filter(fecha__year=year, fecha__gte=hoy)
              .order_by("fecha", "hora_inicio", "titulo")
        )
    else:
        actividades = (
            qs.filter(fecha__year=year)
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


from django.contrib.auth import get_user_model
from notificaciones_app.models import Notification

User = get_user_model()

@login_required
def actividad_create(request):
    """
    Crear actividad + notificación PWA
    """
    if request.method == "POST":
        form = ActividadForm(request.POST)
        if form.is_valid():
            actividad = form.save()

            # ===============================
            # 🔔 NOTIFICACIÓN PWA
            # ===============================
            usuarios = User.objects.filter(is_active=True)

            titulo = "🗓️ Nueva actividad agendada"
            mensaje = f"{actividad.titulo} • {actividad.fecha.strftime('%d/%m/%Y')}"
            url = f"/agenda/actividad/{actividad.id}/"

            for u in usuarios:
                Notification.objects.create(
                    usuario=u,
                    titulo=titulo,
                    mensaje=mensaje,
                    url_destino=url,
                )

            messages.success(request, "✅ Actividad agendada y notificada.")
            return redirect("agenda_app:agenda_anual")
    else:
        form = ActividadForm()

    context = {"form": form}
    return render(request, "agenda_app/actividad_form.html", context)

@login_required
def actividad_detail(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)
    return render(request, "agenda_app/actividad_detail.html", {"actividad": actividad})


@login_required
def actividad_update(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)

    if request.method == "POST":
        form = ActividadForm(request.POST, instance=actividad)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Actividad actualizada correctamente.")
            return redirect("agenda_app:actividad_detail", pk=actividad.pk)
    else:
        form = ActividadForm(instance=actividad)

    return render(request, "agenda_app/actividad_form.html", {"form": form, "actividad": actividad})


@login_required
def actividad_delete(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)

    if request.method == "POST":
        year = actividad.fecha.year
        actividad.delete()
        messages.success(request, "🗑️ Actividad eliminada.")
        return redirect(f"{redirect('agenda_app:agenda_anual').url}?year={year}")

    return render(request, "agenda_app/actividad_confirm_delete.html", {"actividad": actividad})
