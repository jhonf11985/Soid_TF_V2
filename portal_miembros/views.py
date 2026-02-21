from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.db.models import Q

from miembros_app.models import (
    Miembro,
    MiembroRelacion,
    HogarFamiliar,
    HogarMiembro,
    ClanFamiliar,
    sync_familia_inteligente_por_relacion,
    asegurar_hogar_para_miembro,
)
from estructura_app.models import UnidadMembresia, UnidadCargo
from agenda_app.models import Actividad
from formacion_app.models import InscripcionGrupo, GrupoFormativo

from portal_miembros.acceso import acceso_portal_requerido
from .forms import MiembroPortalUpdateForm


# =====================================================================
# DASHBOARD
# =====================================================================

@login_required
@acceso_portal_requerido
def dashboard(request):
    miembro = request.user.miembro

    # ==========================================================
    # 1) UNIDADES donde está (cargos + membresías) + roles
    #    y TODOS los líderes de esas unidades + contactos
    # ==========================================================

    cargos = (
        UnidadCargo.objects
        .select_related("unidad", "rol", "miembo_fk")
        .filter(miembo_fk=miembro, vigente=True)
        .order_by("id")
    )

    membresias = (
        UnidadMembresia.objects
        .select_related("unidad", "rol", "miembo_fk")
        .filter(miembo_fk=miembro, activo=True)
        .order_by("id")
    )

    unidades_map = {}  # key = unidad_id

    def add_unidad(unidad, rol, es_liderazgo=False):
        if not unidad:
            return

        uid = unidad.id
        if uid not in unidades_map:
            unidades_map[uid] = {
                "unidad_id": uid,
                "unidad_nombre": unidad.nombre,
                "roles": [],
                "tiene_liderazgo": False,
                "lideres": [],
            }

        if rol:
            unidades_map[uid]["roles"].append({
                "rol_nombre": getattr(rol, "nombre", "") or "",
                "rol_tipo": getattr(rol, "tipo", "") or "",
            })

        if es_liderazgo:
            unidades_map[uid]["tiene_liderazgo"] = True

    # Cargos = liderazgo
    for c in cargos:
        add_unidad(c.unidad, c.rol, es_liderazgo=True)

    # Membresías = participación / trabajo
    for m in membresias:
        es_lid = (getattr(m.rol, "tipo", "") == "LIDERAZGO")
        add_unidad(m.unidad, m.rol, es_liderazgo=es_lid)

    unidad_ids = list(unidades_map.keys())

    # Buscar TODOS los líderes por unidad
    lideres_qs = (
        UnidadCargo.objects
        .select_related("miembo_fk", "unidad", "rol")
        .filter(unidad_id__in=unidad_ids, vigente=True, rol__tipo="LIDERAZGO")
        .order_by("unidad_id", "id")
    )

    for l in lideres_qs:
        if not l.unidad or l.unidad_id not in unidades_map or not l.miembo_fk:
            continue

        lider_m = l.miembo_fk

        telefono = getattr(lider_m, "telefono", None) or getattr(lider_m, "celular", None) or getattr(lider_m, "movil", None)
        whatsapp = getattr(lider_m, "whatsapp", None) or telefono
        email = getattr(lider_m, "email", None) or getattr(lider_m, "correo", None)

        unidades_map[l.unidad_id]["lideres"].append({
            "id": lider_m.id,
            "nombre": f"{lider_m.nombres} {lider_m.apellidos}".strip(),
            "foto_url": lider_m.foto.url if getattr(lider_m, "foto", None) else None,
            "telefono": telefono,
            "whatsapp": whatsapp,
            "email": email,
            "rol_nombre": getattr(l.rol, "nombre", "") or "Líder",
        })

    # Limpiar roles duplicados
    for uid, u in unidades_map.items():
        seen = set()
        roles_limpios = []
        for r in u["roles"]:
            key = (r.get("rol_nombre"), r.get("rol_tipo"))
            if key in seen:
                continue
            seen.add(key)
            roles_limpios.append(r)
        u["roles"] = roles_limpios

    unidades = list(unidades_map.values())
    unidades.sort(key=lambda x: (not x["tiene_liderazgo"], (x["unidad_nombre"] or "").lower()))

    # ==========================================================
    # 2) PROGRAMAS / GRUPOS donde está asignado + su rol
    # ==========================================================

    inscripciones = (
        InscripcionGrupo.objects
        .select_related("grupo", "grupo__programa", "grupo__ciclo")
        .prefetch_related("grupo__maestros", "grupo__ayudantes")
        .filter(miembro=miembro, estado="ACTIVO", grupo__activo=True)
    )

    grupos_maestro = (
        GrupoFormativo.objects
        .select_related("programa", "ciclo")
        .prefetch_related("maestros", "ayudantes")
        .filter(maestros=miembro, activo=True)
    )

    grupos_ayudante = (
        GrupoFormativo.objects
        .select_related("programa", "ciclo")
        .prefetch_related("maestros", "ayudantes")
        .filter(ayudantes=miembro, activo=True)
    )

    programas_map = {}

    def _nombres_miembros(qs):
        return [f"{m.nombres} {m.apellidos}".strip() for m in qs if m]

    def add_programa(grupo, rol):
        if not grupo:
            return
        gid = grupo.id

        programa_nombre = grupo.programa.nombre if getattr(grupo, "programa", None) else "Grupo formativo"
        ciclo_nombre = grupo.ciclo.nombre if getattr(grupo, "ciclo", None) else None

        if gid not in programas_map:
            maestros_qs = getattr(grupo, "maestros", None)
            ayudantes_qs = getattr(grupo, "ayudantes", None)

            maestros_lista = _nombres_miembros(maestros_qs.all()) if maestros_qs else []
            ayudantes_lista = _nombres_miembros(ayudantes_qs.all()) if ayudantes_qs else []

            programas_map[gid] = {
                "grupo_id": gid,
                "programa_nombre": programa_nombre,
                "ciclo_nombre": ciclo_nombre,
                "grupo_nombre": getattr(grupo, "nombre", "") or "",
                "horario": getattr(grupo, "horario", "") or "",
                "lugar": getattr(grupo, "lugar", "") or "",
                "maestros": maestros_lista,
                "ayudantes": ayudantes_lista,
                "roles": set(),
            }

        programas_map[gid]["roles"].add(rol)

    for ins in inscripciones:
        add_programa(ins.grupo, "Alumno")

    for g in grupos_maestro:
        add_programa(g, "Maestro")

    for g in grupos_ayudante:
        add_programa(g, "Ayudante")

    programas = list(programas_map.values())

    orden_rol = {"Maestro": 0, "Ayudante": 1, "Alumno": 2}
    for p in programas:
        p["roles"] = sorted(list(p["roles"]), key=lambda r: orden_rol.get(r, 99))

    programas.sort(key=lambda x: (
        (x["programa_nombre"] or "").lower(),
        (x["ciclo_nombre"] or "").lower(),
        (x["grupo_nombre"] or "").lower()
    ))

    # ==========================================================
    # 3) ACTIVIDADES PÚBLICAS (próximas)
    # ==========================================================
    actividades = Actividad.objects.filter(
        visibilidad=Actividad.Visibilidad.PUBLICO,
        estado=Actividad.Estado.PROGRAMADA,
        fecha__gte=timezone.now().date()
    ).order_by('fecha', 'hora_inicio')[:5]

    # ==========================================================
    # 4) Render
    # ==========================================================
    context = {
        "miembro": miembro,
        "unidades": unidades,
        "context_programas": programas,
        "actividades": actividades,
    }
    return render(request, "portal_miembros/dashboard.html", context)


# =====================================================================
# PERFIL (solo lectura)
# =====================================================================

@login_required
@acceso_portal_requerido
def perfil(request):
    miembro = request.user.miembro

    context = {
        "miembro": miembro,
    }
    return render(request, "portal_miembros/perfil.html", context)


# =====================================================================
# HELPER: OBTENER CONTEXTO DE FAMILIA
# =====================================================================

def obtener_familia_contexto(miembro):
    """
    Retorna el contexto de familia para un miembro.
    """
    # Hogar principal del miembro
    hogar_miembro = HogarMiembro.objects.filter(
        miembro=miembro, es_principal=True
    ).select_related("hogar", "hogar__clan").first()

    hogar_actual = hogar_miembro.hogar if hogar_miembro else None

    # Relaciones donde este miembro es el "miembro" principal
    relaciones_qs = MiembroRelacion.objects.filter(
        miembro=miembro
    ).select_related("familiar").order_by("tipo_relacion")

    # Construir lista de relaciones para mostrar
    relaciones_lista = []
    
    for rel in relaciones_qs:
        familiar = rel.familiar
        relaciones_lista.append({
            "id": rel.id,
            "tipo": rel.tipo_relacion,
            "tipo_display": rel.get_tipo_relacion_display(),
            "familiar": familiar,
            "familiar_id": familiar.id,
            "familiar_nombre": f"{familiar.nombres} {familiar.apellidos}".strip(),
            "familiar_foto": familiar.foto.url if getattr(familiar, "foto", None) and familiar.foto else None,
            "vive_junto": rel.vive_junto,
            "es_responsable": rel.es_responsable,
        })

    # Miembros del hogar (si tiene hogar)
    miembros_hogar = []
    if hogar_actual:
        miembros_hogar = HogarMiembro.objects.filter(
            hogar=hogar_actual
        ).exclude(miembro=miembro).select_related("miembro")

    return {
        "hogar_actual": hogar_actual,
        "hogar_miembro": hogar_miembro,
        "relaciones": relaciones_lista,
        "relaciones_count": len(relaciones_lista),
        "miembros_hogar": miembros_hogar,
    }


# =====================================================================
# PERFIL EDITAR (con familia)
# =====================================================================

@login_required
@acceso_portal_requerido
def perfil_editar(request):
    """
    Vista de edición de perfil CON soporte para familia.
    """
    miembro = request.user.miembro

    if request.method == "POST":
        form = MiembroPortalUpdateForm(request.POST, request.FILES, instance=miembro)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Tus datos se actualizaron correctamente.")
            return redirect("portal_miembros:perfil")
        else:
            messages.error(request, "⚠️ Revisa los campos marcados. Hay errores en el formulario.")
    else:
        form = MiembroPortalUpdateForm(instance=miembro)

    # Obtener contexto de familia
    familia_ctx = obtener_familia_contexto(miembro)

    # Tipos de relación - usar los del modelo
    tipos_relacion = MiembroRelacion.TIPO_RELACION_CHOICES

    context = {
        "miembro": miembro,
        "form": form,
        # Familia
        "hogar_actual": familia_ctx["hogar_actual"],
        "relaciones": familia_ctx["relaciones"],
        "relaciones_count": familia_ctx["relaciones_count"],
        "miembros_hogar": familia_ctx["miembros_hogar"],
        "tipos_relacion": tipos_relacion,
    }
    return render(request, "portal_miembros/perfil_editar.html", context)


# =====================================================================
# NOTIFICACIONES
# =====================================================================

@login_required
@acceso_portal_requerido
def notificaciones(request):
    return render(request, "portal_miembros/notificaciones.html")


# =====================================================================
# AJAX: BUSCAR MIEMBROS (para autocomplete)
# =====================================================================

@login_required
@acceso_portal_requerido
@require_GET
def ajax_buscar_miembros_portal(request):
    """
    Búsqueda de miembros para el autocomplete del portal.
    """
    q = request.GET.get("q", "").strip()
    miembro_actual = request.user.miembro

    if len(q) < 2:
        return JsonResponse({"results": []})

    # IDs a excluir (el propio miembro + los que ya tienen relación)
    excluir_ids = [miembro_actual.id]
    
    # Obtener IDs de miembros que ya tienen relación
    relaciones_existentes = MiembroRelacion.objects.filter(
        miembro=miembro_actual
    ).values_list("familiar_id", flat=True)
    
    excluir_ids.extend(list(relaciones_existentes))

    # Búsqueda por nombre, apellido o código
    qs = Miembro.objects.exclude(id__in=excluir_ids).filter(
        Q(nombres__icontains=q) |
        Q(apellidos__icontains=q) |
        Q(codigo_miembro__icontains=q)
    ).order_by("nombres", "apellidos")[:15]

    results = []
    for m in qs:
        nombre_completo = f"{m.nombres} {m.apellidos}".strip()
        results.append({
            "id": m.id,
            "nombre": nombre_completo,
            "codigo": getattr(m, "codigo_miembro", "") or "",
            "foto_url": m.foto.url if getattr(m, "foto", None) and m.foto else None,
        })

    return JsonResponse({"results": results})


# =====================================================================
# CREAR HOGAR
# =====================================================================

@login_required
@acceso_portal_requerido
@require_POST
@csrf_protect
@transaction.atomic
def crear_mi_hogar(request):
    """
    Crea un hogar para el miembro actual si no tiene uno.
    """
    miembro = request.user.miembro

    # Verificar si ya tiene hogar principal
    existe = HogarMiembro.objects.filter(miembro=miembro, es_principal=True).exists()
    if existe:
        messages.info(request, "Ya tienes un hogar creado.")
        return redirect("portal_miembros:perfil_editar")

    # Crear hogar usando la función inteligente
    hogar = asegurar_hogar_para_miembro(miembro)

    # Opcionalmente actualizar el nombre
    nombre_hogar = request.POST.get("nombre_hogar", "").strip()
    if nombre_hogar:
        hogar.nombre = nombre_hogar
        hogar.save(update_fields=["nombre"])

    messages.success(request, "✅ Tu hogar fue creado correctamente.")
    return redirect("portal_miembros:perfil_editar")


# =====================================================================
# AJAX: VALIDAR RELACIÓN (tiempo real)
# =====================================================================

@login_required
@acceso_portal_requerido
@require_GET
def ajax_validar_relacion(request):
    """
    Valida una relación familiar en tiempo real (AJAX).
    Retorna errores y warnings sin guardar.
    """
    from miembros_app.validators.relaciones import validar_relacion_familiar
    
    miembro = request.user.miembro
    familiar_id = request.GET.get("familiar_id")
    tipo_relacion = request.GET.get("tipo_relacion")

    if not familiar_id or not tipo_relacion:
        return JsonResponse({
            "valid": False,
            "errors": ["Faltan datos para validar."],
            "warnings": [],
        })

    try:
        familiar = Miembro.objects.get(id=familiar_id)
    except Miembro.DoesNotExist:
        return JsonResponse({
            "valid": False,
            "errors": ["El miembro seleccionado no existe."],
            "warnings": [],
        })

    # Ejecutar validaciones
    resultado = validar_relacion_familiar(
        miembro=miembro,
        familiar=familiar,
        tipo_relacion=tipo_relacion,
    )

    return JsonResponse({
        "valid": resultado["valid"],
        "errors": resultado["errors"],
        "warnings": resultado["warnings"],
    })


# =====================================================================
# AGREGAR RELACIÓN FAMILIAR
# =====================================================================

@login_required
@acceso_portal_requerido
@require_POST
@csrf_protect
@transaction.atomic
def agregar_relacion_portal(request):
    """
    Agrega una relación familiar desde el portal.
    Incluye validaciones completas.
    """
    from miembros_app.validators.relaciones import validar_relacion_familiar
    
    miembro = request.user.miembro

    familiar_id = request.POST.get("familiar_id")
    tipo_relacion = request.POST.get("tipo_relacion")
    vive_junto = request.POST.get("vive_junto") == "on"
    confirmar_warnings = request.POST.get("confirmar_warnings") == "1"

    if not familiar_id or not tipo_relacion:
        messages.error(request, "⚠️ Debes seleccionar un familiar y tipo de relación.")
        return redirect("portal_miembros:perfil_editar")

    # Obtener el familiar
    familiar = get_object_or_404(Miembro, id=familiar_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDACIONES
    # ═══════════════════════════════════════════════════════════════════════════
    resultado = validar_relacion_familiar(
        miembro=miembro,
        familiar=familiar,
        tipo_relacion=tipo_relacion,
    )

    # Si hay errores, no permitir guardar
    if not resultado["valid"]:
        for error in resultado["errors"]:
            messages.error(request, f"❌ {error}")
        return redirect("portal_miembros:perfil_editar")

    # Si hay warnings y no se ha confirmado, mostrar advertencias
    if resultado["warnings"] and not confirmar_warnings:
        for warning in resultado["warnings"]:
            messages.warning(request, f"⚠️ {warning}")
        # Guardar datos en sesión para que el usuario pueda confirmar
        request.session["pending_relacion"] = {
            "familiar_id": familiar_id,
            "tipo_relacion": tipo_relacion,
            "vive_junto": vive_junto,
        }
        messages.info(request, "ℹ️ Si deseas continuar a pesar de las advertencias, vuelve a agregar la relación.")
        return redirect("portal_miembros:perfil_editar")

    # ═══════════════════════════════════════════════════════════════════════════
    # CREAR RELACIÓN
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Crear la relación directa
    relacion = MiembroRelacion.objects.create(
        miembro=miembro,
        familiar=familiar,
        tipo_relacion=tipo_relacion,
        vive_junto=vive_junto,
        es_inferida=False,
    )

    # Sincronizar hogar (esto crea hogares automáticamente)
    try:
        sync_familia_inteligente_por_relacion(relacion)
    except Exception as e:
        print(f"Error en sync_familia: {e}")

    # Crear relación inversa si no existe
    tipo_inverso = MiembroRelacion.inverse_tipo(tipo_relacion, miembro.genero)
    existe_inversa = MiembroRelacion.objects.filter(
        miembro=familiar, familiar=miembro
    ).exists()

    if not existe_inversa:
        MiembroRelacion.objects.create(
            miembro=familiar,
            familiar=miembro,
            tipo_relacion=tipo_inverso,
            vive_junto=vive_junto,
            es_inferida=True,
        )

    # Limpiar sesión si había datos pendientes
    if "pending_relacion" in request.session:
        del request.session["pending_relacion"]

    messages.success(
        request,
        f"✅ Relación agregada: {familiar.nombres} es tu {relacion.get_tipo_relacion_display().lower()}."
    )
    return redirect("portal_miembros:perfil_editar")


# =====================================================================
# ELIMINAR RELACIÓN FAMILIAR
# =====================================================================

@login_required
@acceso_portal_requerido
@require_POST
@csrf_protect
@transaction.atomic
def eliminar_relacion_portal(request, relacion_id):
    """
    Elimina una relación familiar.
    """
    miembro = request.user.miembro

    # Buscar la relación (solo puede eliminar las suyas)
    relacion = get_object_or_404(MiembroRelacion, id=relacion_id, miembro=miembro)

    familiar = relacion.familiar
    tipo_display = relacion.get_tipo_relacion_display()

    # Eliminar la relación inversa (si es inferida)
    MiembroRelacion.objects.filter(
        miembro=familiar,
        familiar=miembro,
        es_inferida=True
    ).delete()

    # Eliminar la relación principal
    relacion.delete()

    messages.success(
        request,
        f"✅ Relación eliminada: {familiar.nombres} ya no aparece como tu {tipo_display.lower()}."
    )
    return redirect("portal_miembros:perfil_editar")


# =====================================================================
# ACTUALIZAR NOMBRE DEL HOGAR
# =====================================================================

@login_required
@acceso_portal_requerido
@require_POST
@csrf_protect
def actualizar_nombre_hogar(request):
    """
    Actualiza el nombre del hogar del miembro.
    """
    miembro = request.user.miembro

    hogar_miembro = HogarMiembro.objects.filter(
        miembro=miembro, es_principal=True
    ).select_related("hogar").first()

    if not hogar_miembro or not hogar_miembro.hogar:
        messages.error(request, "⚠️ No tienes un hogar asignado.")
        return redirect("portal_miembros:perfil_editar")

    nombre = request.POST.get("nombre_hogar", "").strip()
    if nombre:
        hogar_miembro.hogar.nombre = nombre
        hogar_miembro.hogar.save(update_fields=["nombre"])
        messages.success(request, "✅ Nombre del hogar actualizado.")
    else:
        messages.warning(request, "⚠️ El nombre no puede estar vacío.")

    return redirect("portal_miembros:perfil_editar")