from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from miembros_app.models import Miembro
from estructura_app.models import UnidadMembresia, UnidadCargo
from agenda_app.models import Actividad
from formacion_app.models import InscripcionGrupo, GrupoFormativo

from portal_miembros.acceso import acceso_portal_requerido


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


from .forms import MiembroPortalUpdateForm


@login_required
@acceso_portal_requerido
def perfil(request):
    miembro = request.user.miembro

    context = {
        "miembro": miembro,
    }
    return render(request, "portal_miembros/perfil.html", context)


@login_required
@acceso_portal_requerido
def perfil_editar(request):
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

    context = {
        "miembro": miembro,
        "form": form,
    }
    return render(request, "portal_miembros/perfil_editar.html", context)


@login_required
@acceso_portal_requerido
def notificaciones(request):
    return render(request, "portal_miembros/notificaciones.html")