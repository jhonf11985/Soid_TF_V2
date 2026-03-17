# agenda_app/views.py

from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from notificaciones_app.models import Notification
from .models import Actividad
from .forms import ActividadForm


User = get_user_model()

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


def _require_tenant(request):
    """Retorna el tenant o None si no está disponible."""
    return getattr(request, 'tenant', None)


@login_required
def home(request):
    return render(request, "agenda_app/home.html")


@login_required
@permission_required('agenda_app.view_actividad', raise_exception=True)
def agenda_anual(request):
    tenant = _require_tenant(request)
    if not tenant:
        return HttpResponseForbidden("Tenant no disponible.")

    hoy = date.today()

    year_str = request.GET.get("year")
    try:
        year = int(year_str) if year_str else hoy.year
    except ValueError:
        year = hoy.year

    # Base queryset filtrado por tenant
    qs = Actividad.objects.filter(tenant=tenant)

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


@login_required
@permission_required('agenda_app.add_actividad', raise_exception=True)
def actividad_create(request):
    """
    Crear actividad + notificación PWA
    """
    tenant = _require_tenant(request)
    if not tenant:
        return HttpResponseForbidden("Tenant no disponible.")

    if request.method == "POST":
        form = ActividadForm(request.POST, tenant=tenant)
        if form.is_valid():
            actividad = form.save(commit=False)
            actividad.tenant = tenant
            actividad.save()

            # ===============================
            # 🔔 Notificación PWA
            # - Público: a todos los usuarios activos (staff y no staff)
            # - Privado: solo staff activos
            # ===============================
            titulo = "📅 Nueva actividad agendada"
            mensaje = f"Se ha programado: {actividad.titulo} ({actividad.fecha})"
            url = "/agenda/"

            vis = (actividad.visibilidad or "").upper()
            if vis == "PUBLICO":
                usuarios = User.objects.filter(is_active=True)
            else:
                usuarios = User.objects.filter(is_active=True, is_staff=True)

            for u in usuarios:
                Notification.objects.create(
                    tenant=tenant,
                    usuario=u,
                    titulo=titulo,
                    mensaje=mensaje,
                    url_destino=url
                )

            messages.success(request, "✅ Actividad agendada y notificada.")
            return redirect("agenda_app:agenda_anual")
    else:
        form = ActividadForm(tenant=tenant)

    context = {"form": form}
    return render(request, "agenda_app/actividad_form.html", context)


@login_required
@permission_required('agenda_app.view_actividad', raise_exception=True)
def actividad_detail(request, pk):
    tenant = _require_tenant(request)
    if not tenant:
        return HttpResponseForbidden("Tenant no disponible.")

    actividad = get_object_or_404(Actividad, pk=pk, tenant=tenant)
    return render(request, "agenda_app/actividad_detail.html", {"actividad": actividad})


@login_required
@permission_required('agenda_app.change_actividad', raise_exception=True)
def actividad_update(request, pk):
    tenant = _require_tenant(request)
    if not tenant:
        return HttpResponseForbidden("Tenant no disponible.")

    actividad = get_object_or_404(Actividad, pk=pk, tenant=tenant)

    if request.method == "POST":
        form = ActividadForm(request.POST, instance=actividad, tenant=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Actividad actualizada correctamente.")
            return redirect("agenda_app:actividad_detail", pk=actividad.pk)
    else:
        form = ActividadForm(instance=actividad, tenant=tenant)

    return render(request, "agenda_app/actividad_form.html", {"form": form, "actividad": actividad})


@login_required
@permission_required('agenda_app.delete_actividad', raise_exception=True)
def actividad_delete(request, pk):
    tenant = _require_tenant(request)
    if not tenant:
        return HttpResponseForbidden("Tenant no disponible.")

    actividad = get_object_or_404(Actividad, pk=pk, tenant=tenant)

    if request.method == "POST":
        year = actividad.fecha.year
        actividad.delete()
        messages.success(request, "🗑️ Actividad eliminada.")
        return redirect(f"{redirect('agenda_app:agenda_anual').url}?year={year}")

    return render(request, "agenda_app/actividad_confirm_delete.html", {"actividad": actividad})


# ============================================================
# ICS Calendar Export
# ============================================================

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
    tenant = _require_tenant(request)
    if not tenant:
        return HttpResponse("Tenant no disponible.", status=404)

    hoy = timezone.localdate()

    # Solo futuras y programadas, filtradas por tenant
    actividades = (
        Actividad.objects
        .filter(tenant=tenant, fecha__gte=hoy)
        .order_by("fecha", "hora_inicio", "titulo")
    )

    now_utc_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # Nombre del calendario basado en tenant
    cal_name = f"{tenant.nombre} - Agenda" if hasattr(tenant, 'nombre') else "SOID - Agenda"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SOID//Agenda Iglesia//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ics_escape(cal_name)}",
        "X-WR-TIMEZONE:America/Santo_Domingo",
    ]

    for a in actividades:
        # UID estable por actividad (incluye tenant para unicidad)
        uid = f"soid-actividad-{tenant.id}-{a.id}@soid"

        summary = _ics_escape(a.titulo)
        description = _ics_escape(a.descripcion or "")
        location = _ics_escape(a.lugar or "")

        # Estado
        status = "CONFIRMED"
        if a.estado == Actividad.Estado.CANCELADA:
            status = "CANCELLED"

        # Si no hay hora, lo tratamos como "all-day event"
        if not a.hora_inicio:
            dtstart = a.fecha.strftime("%Y%m%d")
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
            # Evento con hora
            tz = timezone.get_current_timezone()
            inicio_local = timezone.make_aware(datetime.combine(a.fecha, a.hora_inicio), tz)

            if a.hora_fin:
                fin_local = timezone.make_aware(datetime.combine(a.fecha, a.hora_fin), tz)
            else:
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


def calendario_info(request):
    return render(request, "agenda_app/calendario_info.html")