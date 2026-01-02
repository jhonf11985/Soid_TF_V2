from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from miembros_app.models import Miembro
from .forms import NuevoCreyenteExpedienteForm
from .models import NuevoCreyenteExpediente


@require_POST
@login_required
def seguimiento_padre_add(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    padre_id = (request.POST.get("padre_espiritual_id") or "").strip()
    if padre_id:
        try:
            padre = Miembro.objects.get(pk=int(padre_id))
            expediente.padres_espirituales.add(padre)
            messages.success(request, "Padre espiritual añadido.")
        except (ValueError, Miembro.DoesNotExist):
            messages.error(request, "Padre espiritual inválido.")
    else:
        messages.error(request, "Selecciona un padre espiritual para añadir.")

    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)


@require_POST
@login_required
def seguimiento_padre_remove(request, miembro_id, padre_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    try:
        padre = Miembro.objects.get(pk=int(padre_id))
        expediente.padres_espirituales.remove(padre)
        messages.success(request, "Padre espiritual quitado.")
    except (ValueError, Miembro.DoesNotExist):
        messages.error(request, "Padre espiritual inválido.")

    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)


@login_required
def dashboard(request):
    total_nc = Miembro.objects.filter(nuevo_creyente=True).count()
    context = {"total_nc": total_nc}
    return render(request, "nuevo_creyente_app/dashboard.html", context)


@login_required
def seguimiento_lista(request):
    query = request.GET.get("q", "").strip()
    genero_filtro = request.GET.get("genero", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()
    solo_contacto = request.GET.get("solo_contacto", "") == "1"

    qs = (
        Miembro.objects
        .filter(expediente_nuevo_creyente__isnull=False)
        .select_related("expediente_nuevo_creyente")
    )

    if query:
        qs = qs.filter(
            Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(telefono__icontains=query)
            | Q(telefono_secundario__icontains=query)
            | Q(email__icontains=query)
            | Q(codigo_seguimiento__icontains=query)
        )

    if genero_filtro:
        qs = qs.filter(genero=genero_filtro)

    if fecha_desde:
        try:
            qs = qs.filter(fecha_conversion__gte=fecha_desde)
        except ValueError:
            pass

    if fecha_hasta:
        try:
            qs = qs.filter(fecha_conversion__lte=fecha_hasta)
        except ValueError:
            pass

    if solo_contacto:
        qs = qs.filter(
            Q(telefono__isnull=False, telefono__gt="")
            | Q(telefono_secundario__isnull=False, telefono_secundario__gt="")
            | Q(email__isnull=False, email__gt="")
            | Q(whatsapp__isnull=False, whatsapp__gt="")
        )

    qs = qs.order_by(
        "-fecha_conversion",
        "-fecha_creacion",
        "apellidos",
        "nombres",
    )

    generos_choices = Miembro._meta.get_field("genero").choices

    context = {
        "miembros": qs,
        "query": query,
        "genero_filtro": genero_filtro,
        "generos_choices": generos_choices,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "solo_contacto": solo_contacto,
        "hoy": timezone.localdate(),
        "total": qs.count(),
    }
    return render(request, "nuevo_creyente_app/seguimiento_lista.html", context)


@login_required
def seguimiento_detalle(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    if request.method == "POST":
        form = NuevoCreyenteExpedienteForm(request.POST, instance=expediente)
        if form.is_valid():
            form.save()
            messages.success(request, "Seguimiento actualizado correctamente.")
            return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)
        else:
            messages.error(request, "Revisa los campos. Hay errores en el formulario.")
    else:
        form = NuevoCreyenteExpedienteForm(instance=expediente)

    context = {
        "miembro": miembro,
        "expediente": expediente,
        "form": form,
        "hoy": timezone.localdate(),
    }
    return render(request, "nuevo_creyente_app/seguimiento_detalle.html", context)


# ✅ NUEVO: cambiar etapa del ciclo (manual asistido)
@require_POST
@login_required
def seguimiento_set_etapa(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    etapa = (request.POST.get("etapa") or "").strip()

    # Validar etapa
    etapas_validas = [e[0] for e in NuevoCreyenteExpediente.Etapas.choices]
    if etapa not in etapas_validas:
        messages.error(request, "Etapa inválida.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # Si está cerrado, no dejar cambiar
    if expediente.estado == NuevoCreyenteExpediente.Estados.CERRADO:
        messages.error(request, "Este seguimiento está cerrado. No se puede cambiar la etapa.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    expediente.etapa = etapa
    expediente.save(update_fields=["etapa", "fecha_actualizacion"])

    messages.success(request, "Etapa actualizada.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)


# ✅ NUEVO: cerrar seguimiento
@require_POST
@login_required
def seguimiento_cerrar(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    if expediente.estado == NuevoCreyenteExpediente.Estados.CERRADO:
        messages.info(request, "Este seguimiento ya está cerrado.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    if not expediente.puede_cerrar():
        messages.error(request, "Para cerrar, coloca la etapa en 'Evaluación'.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    expediente.cerrar(user=request.user)
    messages.success(request, "Seguimiento cerrado correctamente.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)
