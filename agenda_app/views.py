from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required

from django.shortcuts import render, redirect, get_object_or_404

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
@permission_required('agenda_app.view_actividad', raise_exception=True)
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
@permission_required('agenda_app.add_actividad', raise_exception=True)
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
@permission_required('agenda_app.view_actividad', raise_exception=True)
def actividad_detail(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)
    return render(request, "agenda_app/actividad_detail.html", {"actividad": actividad})


@login_required
@permission_required('agenda_app.change_actividad', raise_exception=True)
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
@permission_required('agenda_app.delete_actividad', raise_exception=True)
def actividad_delete(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)

    if request.method == "POST":
        year = actividad.fecha.year
        actividad.delete()
        messages.success(request, "🗑️ Actividad eliminada.")
        return redirect(f"{redirect('agenda_app:agenda_anual').url}?year={year}")

    return render(request, "agenda_app/actividad_confirm_delete.html", {"actividad": actividad})

from datetime import datetime, timedelta
from django.http import HttpResponse
from django.utils import timezone


def _ics_escape(value: str) -> str:
    """
    Escapar texto para ICS (RFC 5545):
    - \  -> \\
    - ;  -> \;
    - ,  -> \,
    - saltos de línea -> \n
    """
    if value is None:
        return ""
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace(";", "\\;")
    value = value.replace(",", "\\,")
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    return value


from datetime import timezone as dt_timezone

def _dt_utc_str(dt: datetime) -> str:
    """
    Formato UTC para ICS: YYYYMMDDTHHMMSSZ
    """
    dt_utc = dt.astimezone(dt_timezone.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")


def calendario_ics(request):
    """
    Calendario ICS público (solo lectura) para actividades de SOID.
    Los miembros agregan este link a Google Calendar / iPhone / Outlook.
    """
    hoy = timezone.localdate()

    # Básico: solo futuras y programadas
    actividades = (
        Actividad.objects
        .filter(fecha__gte=hoy)
        .order_by("fecha", "hora_inicio", "titulo")
    )

    now_utc_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SOID//Agenda Iglesia//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:SOID - Agenda",
        "X-WR-TIMEZONE:America/Santo_Domingo",

    ]

    for a in actividades:
        # UID estable por actividad
        uid = f"soid-actividad-{a.id}@soid"

        summary = _ics_escape(a.titulo)
        description = _ics_escape(a.descripcion or "")
        location = _ics_escape(a.lugar or "")

        # Estado
        # PROGRAMADA -> CONFIRMED
        # CANCELADA -> CANCELLED
        status = "CONFIRMED"
        if a.estado == Actividad.Estado.CANCELADA:
            status = "CANCELLED"

        # Si no hay hora, lo tratamos como "all-day event"
        if not a.hora_inicio:
            dtstart = a.fecha.strftime("%Y%m%d")
            # En eventos de día completo, DTEND suele ser el día siguiente
            dtend = (a.fecha + timedelta(days=1)).strftime("%Y%m%d")

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_utc_stamp}",
                f"LAST-MODIFIED:{now_utc_stamp}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                f"LOCATION:{location}",
                f"STATUS:{status}",
                f"DTSTART;VALUE=DATE:{dtstart}",
                f"DTEND;VALUE=DATE:{dtend}",
                "END:VEVENT",
            ])
        else:
            # Evento con hora: crear datetimes aware (zona local del proyecto)
            tz = timezone.get_current_timezone()
            inicio_local = timezone.make_aware(datetime.combine(a.fecha, a.hora_inicio), tz)

            if a.hora_fin:
                fin_local = timezone.make_aware(datetime.combine(a.fecha, a.hora_fin), tz)
            else:
                # Si no hay fin, por defecto +1 hora
                fin_local = inicio_local + timedelta(hours=1)

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_utc_stamp}",
                f"LAST-MODIFIED:{now_utc_stamp}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                f"LOCATION:{location}",
                f"STATUS:{status}",
                f"DTSTART:{inicio_local.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{fin_local.strftime('%Y%m%dT%H%M%S')}",

                "END:VEVENT",
            ])

    lines.append("END:VCALENDAR")

    content = "\r\n".join(lines) + "\r\n"
    response = HttpResponse(content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = "inline; filename=soid_agenda.ics"
    response["Cache-Control"] = "no-cache"
    return response
