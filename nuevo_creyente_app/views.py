from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from miembros_app.models import Miembro
from .forms import NuevoCreyenteExpedienteForm
from .models import NuevoCreyenteExpediente
from estructura_app.models import UnidadMembresia, UnidadCargo
from datetime import timedelta
from django.db.models import Count, Q
from miembros_app.models import Miembro  # ajusta si tu import es distinto

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

            # ✅ Bitácora
            expediente.log_padre(
                accion="add",
                padre_miembro_id=padre.id,
                padre_nombre=f"{padre.nombres} {padre.apellidos}".strip(),
                user=request.user,
            )

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

        # ✅ Bitácora
        expediente.log_padre(
            accion="remove",
            padre_miembro_id=padre.id,
            padre_nombre=f"{padre.nombres} {padre.apellidos}".strip(),
            user=request.user,
        )

        messages.success(request, "Padre espiritual quitado.")
    except (ValueError, Miembro.DoesNotExist):
        messages.error(request, "Padre espiritual inválido.")

    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)




@login_required
def dashboard(request):
    hoy = timezone.localdate()
    manana = hoy + timedelta(days=1)

    # Base: expedientes existentes
    qs = NuevoCreyenteExpediente.objects.select_related("miembro").all()

    total_expedientes = qs.count()
    en_seguimiento = qs.filter(estado=NuevoCreyenteExpediente.Estados.EN_SEGUIMIENTO).count()
    cerrados = qs.filter(estado=NuevoCreyenteExpediente.Estados.CERRADO).count()

    # Por etapa (solo en seguimiento)
    etapas = dict(NuevoCreyenteExpediente.Etapas.choices)
    conteo_etapas = (
        qs.filter(estado=NuevoCreyenteExpediente.Estados.EN_SEGUIMIENTO)
          .values("etapa")
          .annotate(total=Count("id"))
          .order_by("etapa")
    )
    conteo_etapas_map = {x["etapa"]: x["total"] for x in conteo_etapas}

    # Alertas de próximo contacto
    con_proximo = qs.filter(estado=NuevoCreyenteExpediente.Estados.EN_SEGUIMIENTO, proximo_contacto__isnull=False)
    prox_hoy = con_proximo.filter(proximo_contacto=hoy).count()
    prox_manana = con_proximo.filter(proximo_contacto=manana).count()
    atrasados = con_proximo.filter(proximo_contacto__lt=hoy).count()
    sin_proximo = qs.filter(
        estado=NuevoCreyenteExpediente.Estados.EN_SEGUIMIENTO,
        proximo_contacto__isnull=True
    ).count()

    # Listas rápidas
    ultimos_enviados = (
        qs.order_by("-fecha_envio")
          .select_related("miembro")[:6]
    )

    proximos_contactos = (
        con_proximo.filter(proximo_contacto__in=[hoy, manana])
                  .order_by("proximo_contacto", "-fecha_envio")[:8]
    )

    context = {
        "hoy": hoy,
        "total_expedientes": total_expedientes,
        "en_seguimiento": en_seguimiento,
        "cerrados": cerrados,

        "etapas": etapas,
        "conteo_etapas": conteo_etapas_map,

        "prox_hoy": prox_hoy,
        "prox_manana": prox_manana,
        "atrasados": atrasados,
        "sin_proximo": sin_proximo,

        "ultimos_enviados": ultimos_enviados,
        "proximos_contactos": proximos_contactos,
    }
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
        .prefetch_related("expediente_nuevo_creyente__padres_espirituales")  # clave
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

    hoy = timezone.localdate()

    miembros = list(qs)  # ✅ ahora sí existe
    for m in miembros:
        exp = getattr(m, "expediente_nuevo_creyente", None)
        if exp and exp.fecha_envio:
            m.nc_dias = max((hoy - exp.fecha_envio.date()).days, 0)
        else:
            m.nc_dias = None

    generos_choices = Miembro._meta.get_field("genero").choices

    context = {
        "miembros": miembros,  # ✅ pasamos la lista con nc_dias calculado
        "query": query,
        "genero_filtro": genero_filtro,
        "generos_choices": generos_choices,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "solo_contacto": solo_contacto,
        "hoy": hoy,
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

    # ===============================
    # UNIDADES ASIGNADAS (ESTRUCTURA)
    # ===============================
    membresias_unidad = (
        UnidadMembresia.objects
        .filter(miembo_fk=miembro)
        .select_related("unidad", "rol")
        .order_by("-activo", "unidad__nombre")
    )

    cargos_unidad = (
        UnidadCargo.objects
        .filter(miembo_fk=miembro)
        .select_related("unidad", "rol")
        .order_by("-vigente", "unidad__nombre")
    )

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
        "cargos_unidad": cargos_unidad,
        "membresias_unidad": membresias_unidad,
    }
    return render(request, "nuevo_creyente_app/seguimiento_detalle.html", context)

@require_POST
@login_required
def seguimiento_set_etapa(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    etapa_nueva = (request.POST.get("etapa") or "").strip()

    # Validar etapa
    etapas_validas = [e[0] for e in NuevoCreyenteExpediente.Etapas.choices]
    if etapa_nueva not in etapas_validas:
        messages.error(request, "Etapa inválida.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # Si está cerrado, no dejar cambiar
    if expediente.estado == NuevoCreyenteExpediente.Estados.CERRADO:
        messages.error(request, "Este seguimiento está cerrado. No se puede cambiar la etapa.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    etapa_anterior = expediente.etapa

    # Si no cambia, no hacer nada
    if etapa_anterior == etapa_nueva:
        messages.info(request, "La etapa ya estaba seleccionada.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    expediente.etapa = etapa_nueva
    expediente.save(update_fields=["etapa", "fecha_actualizacion"])

    # ✅ Bitácora
    expediente.log_cambio_etapa(
        etapa_from=etapa_anterior,
        etapa_to=etapa_nueva,
        user=request.user,
    )

    messages.success(request, "Etapa actualizada.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

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

    # ✅ Bitácora
    expediente.log_cierre(user=request.user)

    messages.success(request, "Seguimiento cerrado correctamente.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

from datetime import date

@require_POST
@login_required
def seguimiento_primer_contacto(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    if expediente.estado == NuevoCreyenteExpediente.Estados.CERRADO:
        messages.error(request, "Este expediente está cerrado. No se pueden registrar acciones.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    fecha_str = (request.POST.get("fecha_contacto") or "").strip()
    canal = (request.POST.get("canal") or "").strip()
    resultado = (request.POST.get("resultado") or "").strip()
    nota = (request.POST.get("nota") or "").strip()

    if not fecha_str or not canal or not resultado or not nota:
        messages.error(request, "Completa fecha, canal, resultado y nota.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # Parse fecha
    try:
        fecha_contacto = date.fromisoformat(fecha_str)
    except ValueError:
        messages.error(request, "La fecha del contacto no es válida.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # Crear entrada de bitácora (CONTACTO)
    # Nota: guardamos la nota en detalle, y canal/resultado en sus campos.
    expediente.log_event(
        tipo="contacto",
        titulo="Primer contacto registrado",
        detalle=nota,
        user=request.user,
        canal=canal,
        resultado_contacto=resultado,
    )

    # Opcional: si aún estaba en INICIO, pasar a PRIMER_CONTACTO automáticamente
    if expediente.etapa == "INICIO":
        expediente.etapa = "PRIMER_CONTACTO"
        expediente.save(update_fields=["etapa", "fecha_actualizacion"])
        expediente.log_cambio_etapa(etapa_from="INICIO", etapa_to="PRIMER_CONTACTO", user=request.user)
    else:
        # al menos refresca fecha_actualizacion
        expediente.save(update_fields=["fecha_actualizacion"])

    messages.success(request, "Primer contacto guardado y registrado en la bitácora.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

@require_POST
@login_required
def seguimiento_nota_add(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    if expediente.estado == NuevoCreyenteExpediente.Estados.CERRADO:
        messages.error(request, "Este expediente está cerrado. No se pueden añadir notas.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    texto = (request.POST.get("texto") or "").strip()
    if not texto:
        messages.error(request, "Escribe una nota antes de añadirla.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    expediente.log_nota(texto=texto, user=request.user)
    expediente.save(update_fields=["fecha_actualizacion"])

    messages.success(request, "Nota añadida a la bitácora.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)



@require_POST
@login_required
def seguimiento_acompanamiento_add(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    if expediente.estado == NuevoCreyenteExpediente.Estados.CERRADO:
        messages.error(request, "Este expediente está cerrado. No se pueden registrar acciones.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # ✅ Campos PROPIOS de ACOMPANAMIENTO
    fecha_str = (request.POST.get("fecha_evento") or "").strip()
    tipo_acomp = (request.POST.get("tipo_acompanamiento") or "").strip()
    estado_persona = (request.POST.get("estado_persona") or "").strip()
    nota = (request.POST.get("nota") or "").strip()
    prox_fecha_str = (request.POST.get("proximo_contacto") or "").strip()

    if not fecha_str or not tipo_acomp or not estado_persona or not nota:
        messages.error(request, "Completa fecha, tipo de acompañamiento, estado y nota.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # Parse fecha_evento
    try:
        fecha_evento = date.fromisoformat(fecha_str)
    except ValueError:
        messages.error(request, "La fecha del acompañamiento no es válida.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # (Opcional) Parse próximo contacto
    proximo_contacto = None
    if prox_fecha_str:
        try:
            proximo_contacto = date.fromisoformat(prox_fecha_str)
        except ValueError:
            messages.error(request, "La fecha del próximo contacto no es válida.")
            return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # ✅ Guardar en bitácora como ACOMPANAMIENTO (acción distinta)
    # Reutilizamos canal/resultado_contacto como "tipo_acompanamiento" y "estado_persona"
    expediente.log_event(
        tipo="acompanamiento",
        titulo="Encuentro de acompañamiento",
        detalle=nota,
        user=request.user,
        canal=tipo_acomp,
        resultado_contacto=estado_persona,
    )

    # ✅ Si estaba en PRIMER_CONTACTO, al registrar acompañamiento sugerimos avanzar a ACOMPANAMIENTO
    # (NO lo forzamos si no quieres; aquí lo pongo automático solo cuando todavía está en PRIMER_CONTACTO)
    if expediente.etapa == "PRIMER_CONTACTO":
        expediente.etapa = "ACOMPANAMIENTO"
        expediente.save(update_fields=["etapa", "fecha_actualizacion"])
        expediente.log_cambio_etapa(etapa_from="PRIMER_CONTACTO", etapa_to="ACOMPANAMIENTO", user=request.user)
    else:
        expediente.save(update_fields=["fecha_actualizacion"])

    # ✅ Guardar próximo contacto si lo enviaron
    if proximo_contacto:
        expediente.proximo_contacto = proximo_contacto
        expediente.save(update_fields=["proximo_contacto", "fecha_actualizacion"])

    messages.success(request, "Acompañamiento registrado en la bitácora.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)


@require_POST
@login_required
def seguimiento_integracion_add(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    if expediente.estado == NuevoCreyenteExpediente.Estados.CERRADO:
        messages.error(request, "Este expediente está cerrado. No se pueden registrar acciones.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    fecha_str = (request.POST.get("fecha_integracion") or "").strip()
    tipo_integracion = (request.POST.get("tipo_integracion") or "").strip()
    destino = (request.POST.get("destino") or "").strip()
    responsable_txt = (request.POST.get("responsable_txt") or "").strip()
    proximo_paso = (request.POST.get("proximo_paso") or "").strip()
    nota = (request.POST.get("nota") or "").strip()

    if not fecha_str or not tipo_integracion or not destino:
        messages.error(request, "Completa fecha, tipo de integración y a dónde se integró.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    try:
        fecha_integracion = date.fromisoformat(fecha_str)
    except ValueError:
        messages.error(request, "La fecha de integración no es válida.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # Guardamos un resumen bonito en el detalle
    detalle = f"Destino: {destino}"
    if responsable_txt:
        detalle += f"\nResponsable/contacto: {responsable_txt}"
    if proximo_paso:
        detalle += f"\nPróximo paso: {proximo_paso}"
    if nota:
        detalle += f"\nNota: {nota}"

    expediente.log_event(
        tipo="integracion",
        titulo="Integración registrada",
        detalle=detalle,
        user=request.user,
        canal=tipo_integracion,           # reutilizamos 'canal' como tipo de integración
        resultado_contacto=proximo_paso,  # reutilizamos para el próximo paso (opcional)
    )

    # Si quieres: al registrar integración, sugerimos mover etapa a INTEGRACION (o mantener)
    if expediente.etapa != "INTEGRACION":
        etapa_from = expediente.etapa
        expediente.etapa = "INTEGRACION"
        expediente.save(update_fields=["etapa", "fecha_actualizacion"])
        expediente.log_cambio_etapa(etapa_from=etapa_from, etapa_to="INTEGRACION", user=request.user)
    else:
        expediente.save(update_fields=["fecha_actualizacion"])

    messages.success(request, "Integración registrada.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)



@require_POST
@login_required
def seguimiento_evaluacion_add(request, miembro_id):
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    if expediente.estado == NuevoCreyenteExpediente.Estados.CERRADO:
        messages.error(request, "Este expediente está cerrado. No se pueden registrar acciones.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # Campos
    fecha_str = (request.POST.get("fecha_evaluacion") or "").strip()
    decision = (request.POST.get("decision") or "").strip()
    nota = (request.POST.get("nota") or "").strip()

    # Checkboxes (pueden venir múltiples)
    barreras = request.POST.getlist("barreras")

    if not fecha_str or not decision or not nota:
        messages.error(request, "Completa fecha, decisión y nota final.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    try:
        fecha_eval = date.fromisoformat(fecha_str)
    except ValueError:
        messages.error(request, "La fecha de evaluación no es válida.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    # Construir detalle “bonito”
    barreras_txt = ", ".join(barreras) if barreras else "—"
    detalle = (
        f"Fecha: {fecha_eval}\n"
        f"Barreras: {barreras_txt}\n"
        f"Decisión: {decision}\n\n"
        f"Nota:\n{nota}"
    )

    # ✅ Registrar evento Evaluación en bitácora
    expediente.log_event(
        tipo="evaluacion",
        titulo="Evaluación registrada",
        detalle=detalle,
        user=request.user,
    )

    # ✅ Asegurar etapa EVALUACION (si no lo estaba)
    if expediente.etapa != NuevoCreyenteExpediente.Etapas.EVALUACION:
        etapa_from = expediente.etapa
        expediente.etapa = NuevoCreyenteExpediente.Etapas.EVALUACION
        expediente.save(update_fields=["etapa", "fecha_actualizacion"])
        expediente.log_cambio_etapa(etapa_from=etapa_from, etapa_to=NuevoCreyenteExpediente.Etapas.EVALUACION, user=request.user)
    else:
        expediente.save(update_fields=["fecha_actualizacion"])

    # ✅ Si la decisión es cerrar, cerramos en el acto (usando tus reglas)
    if decision == "cerrar":
        # Ya estamos en evaluación, así que puede cerrar (tu método lo valida a nivel de flujo) :contentReference[oaicite:5]{index=5}
        expediente.cerrar(user=request.user)
        expediente.log_cierre(user=request.user)  # bitácora cierre :contentReference[oaicite:6]{index=6}
        messages.success(request, "Evaluación registrada y seguimiento cerrado.")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    messages.success(request, "Evaluación registrada.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)


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

    resultado_final = (request.POST.get("resultado_final") or "").strip()
    siguiente_paso = (request.POST.get("siguiente_paso") or "").strip()
    nota_cierre = (request.POST.get("nota_cierre") or "").strip()

    if not nota_cierre:
        messages.error(request, "Para cerrar, escribe un resumen (nota final).")
        return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

    detalle = ""
    if resultado_final:
        detalle += f"Resultado: {resultado_final}\n"
    if siguiente_paso:
        detalle += f"Siguiente paso: {siguiente_paso}\n"
    if detalle:
        detalle += "\n"
    detalle += nota_cierre

    expediente.cerrar(user=request.user)  # cambia estado/etapa/fecha :contentReference[oaicite:6]{index=6}

    # Un solo evento “cierre” con detalle (no usamos log_cierre genérico)
    expediente.log_event(
        tipo="cierre",
        titulo="Seguimiento cerrado",
        detalle=detalle,
        user=request.user,
    )

    messages.success(request, "Seguimiento cerrado correctamente.")
    return redirect("nuevo_creyente_app:seguimiento_detalle", miembro_id=miembro.id)

from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

@login_required
def seguimiento_inbox(request):
    """
    Bandeja CRM para seguimiento de nuevos creyentes:
    - Atrasados
    - Para hoy
    - Sin próximo contacto
    """
    hoy = timezone.localdate()
    manana = hoy + timedelta(days=1)

    # Expedientes en seguimiento
    qs = (
        NuevoCreyenteExpediente.objects
        .select_related("miembro", "responsable")
        .prefetch_related("padres_espirituales")
        .filter(estado=NuevoCreyenteExpediente.Estados.EN_SEGUIMIENTO)
    )

    # Opcional: búsqueda rápida por nombre/teléfono/código
    query = (request.GET.get("q") or "").strip()
    if query:
        qs = qs.filter(
            Q(miembro__nombres__icontains=query)
            | Q(miembro__apellidos__icontains=query)
            | Q(miembro__telefono__icontains=query)
            | Q(miembro__telefono_secundario__icontains=query)
            | Q(miembro__whatsapp__icontains=query)
            | Q(miembro__email__icontains=query)
            | Q(miembro__codigo_seguimiento__icontains=query)
        )

    con_proximo = qs.filter(proximo_contacto__isnull=False)

    atrasados = con_proximo.filter(proximo_contacto__lt=hoy).order_by("proximo_contacto", "-fecha_envio")
    para_hoy = con_proximo.filter(proximo_contacto=hoy).order_by("-fecha_envio")
    para_manana = con_proximo.filter(proximo_contacto=manana).order_by("-fecha_envio")

    sin_proximo = qs.filter(proximo_contacto__isnull=True).order_by("-fecha_envio")

    # Contadores (para chips/estadísticas)
    context = {
        "hoy": hoy,
        "query": query,

        "cnt_atrasados": atrasados.count(),
        "cnt_hoy": para_hoy.count(),
        "cnt_manana": para_manana.count(),
        "cnt_sin_proximo": sin_proximo.count(),

        # listas (limitadas para no hacer la página pesada)
        "atrasados": atrasados[:25],
        "para_hoy": para_hoy[:25],
        "para_manana": para_manana[:12],
        "sin_proximo": sin_proximo[:25],
    }
    return render(request, "nuevo_creyente_app/seguimiento_inbox.html", context)


from datetime import date, timedelta
from django.views.decorators.http import require_http_methods

@login_required
def seguimiento_accion(request, miembro_id):
    """
    Pantalla CRM de Acción Rápida.
    - No es el expediente completo.
    - Es la pantalla diaria para registrar acciones en 10-15 segundos.
    """
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    # Sugerencia por defecto: +7 días
    hoy = timezone.localdate()
    sugerido = hoy + timedelta(days=7)

    context = {
        "miembro": miembro,
        "expediente": expediente,
        "hoy": hoy,
        "sugerido_proximo": sugerido,
    }
    return render(request, "nuevo_creyente_app/seguimiento_accion.html", context)


@require_POST
@login_required
def seguimiento_accion_guardar(request, miembro_id):
    """
    Guarda una acción rápida:
    - tipo_accion: llamada / whatsapp / reunion / no_responde / nota
    - resultado: (texto corto)
    - nota: (texto)
    - proximo_contacto: YYYY-MM-DD (opcional)
    - auto-etapa: (opcional) si quieres automatizar avances
    """
    miembro = get_object_or_404(
        Miembro.objects.select_related("expediente_nuevo_creyente"),
        pk=miembro_id,
        expediente_nuevo_creyente__isnull=False,
    )
    expediente = miembro.expediente_nuevo_creyente

    if expediente.estado == NuevoCreyenteExpediente.Estados.CERRADO:
        messages.error(request, "Este expediente está cerrado. No se pueden registrar acciones.")
        return redirect("nuevo_creyente_app:seguimiento_accion", miembro_id=miembro.id)

    tipo_accion = (request.POST.get("tipo_accion") or "").strip()
    resultado = (request.POST.get("resultado") or "").strip()
    nota = (request.POST.get("nota") or "").strip()
    prox_str = (request.POST.get("proximo_contacto") or "").strip()

    if tipo_accion not in ["llamada", "whatsapp", "reunion", "no_responde", "nota"]:
        messages.error(request, "Acción inválida.")
        return redirect("nuevo_creyente_app:seguimiento_accion", miembro_id=miembro.id)

    # Reglas mínimas
    if tipo_accion != "nota" and not resultado:
        messages.error(request, "Selecciona un resultado.")
        return redirect("nuevo_creyente_app:seguimiento_accion", miembro_id=miembro.id)

    if not nota and tipo_accion in ["llamada", "whatsapp", "reunion", "no_responde"]:
        # Nota obligatoria para acciones de contacto (para que no sea “vacío”)
        messages.error(request, "Escribe una nota corta (qué pasó / qué acordaron).")
        return redirect("nuevo_creyente_app:seguimiento_accion", miembro_id=miembro.id)

    # Parse próximo contacto
    proximo_contacto = None
    if prox_str:
        try:
            proximo_contacto = date.fromisoformat(prox_str)
        except ValueError:
            messages.error(request, "La fecha del próximo contacto no es válida.")
            return redirect("nuevo_creyente_app:seguimiento_accion", miembro_id=miembro.id)

    # Título bonito para timeline/bitácora
    TITULOS = {
        "llamada": "Llamada registrada",
        "whatsapp": "Mensaje WhatsApp registrado",
        "reunion": "Reunión registrada",
        "no_responde": "Intento sin respuesta",
        "nota": "Nota rápida",
    }
    titulo = TITULOS.get(tipo_accion, "Acción registrada")

    # Guardar en bitácora usando tu mismo patrón (log_event) :contentReference[oaicite:2]{index=2}
    # Reusamos:
    # - canal = tipo_accion (o un canal humano)
    # - resultado_contacto = resultado
    expediente.log_event(
        tipo="accion",
        titulo=titulo,
        detalle=nota or resultado,
        user=request.user,
        canal=tipo_accion,
        resultado_contacto=resultado,
    )

    # Actualizar próximo contacto si viene
    if proximo_contacto:
        expediente.proximo_contacto = proximo_contacto

    # (Opcional) Automatizar etapa sin preguntarle al usuario (CRM-style)
    # Solo una regla simple: si estaba INICIO y registró llamada/whatsapp/reunion, pasar a PRIMER_CONTACTO
    if expediente.etapa == "INICIO" and tipo_accion in ["llamada", "whatsapp", "reunion"]:
        etapa_from = expediente.etapa
        expediente.etapa = "PRIMER_CONTACTO"
        expediente.save(update_fields=["etapa", "proximo_contacto", "fecha_actualizacion"])
        expediente.log_cambio_etapa(etapa_from=etapa_from, etapa_to="PRIMER_CONTACTO", user=request.user)
    else:
        expediente.save(update_fields=["proximo_contacto", "fecha_actualizacion"])

    messages.success(request, "Acción guardada. ✅")
    return redirect("nuevo_creyente_app:seguimiento_inbox")
