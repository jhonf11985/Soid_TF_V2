from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.shortcuts import get_object_or_404
from miembros_app.models import Miembro  # 👈 usamos el mismo modelo Miembro
from .forms import NuevoCreyenteExpedienteForm


@login_required
def dashboard(request):
    """
    Dashboard básico del módulo Nuevo Creyente.
    """
    total_nc = Miembro.objects.filter(nuevo_creyente=True).count()

    context = {
        "total_nc": total_nc,
    }
    return render(request, "nuevo_creyente_app/dashboard.html", context)


@login_required
def seguimiento_lista(request):
    """
    Lista del módulo Nuevo Creyente (NC).
    Por ahora: todo Miembro con nuevo_creyente=True.
    Luego, cuando implementemos 'expediente', aquí filtraremos por 'en seguimiento'.
    """
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

    generos_choices = Miembro._meta.get_field("genero").choices  # :contentReference[oaicite:2]{index=2}

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
    """
    Detalle del seguimiento de un Nuevo Creyente.
    Permite editar responsable / próximo contacto / notas (inline).
    """
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False
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
