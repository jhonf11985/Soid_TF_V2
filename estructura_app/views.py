from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from miembros_app.models import Miembro
from django.views.decorators.http import require_POST
from .forms import UnidadForm, RolUnidadForm
from .models import Unidad, RolUnidad

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from .models import Unidad, TipoUnidad, RolUnidad, UnidadMembresia, UnidadCargo

@login_required
def estructura_home(request):
    return render(request, "estructura_app/home.html")



@login_required
def dashboard(request):
    # KPIs
    total_unidades = Unidad.objects.count()
    total_tipos = TipoUnidad.objects.filter(activo=True).count()
    total_roles = RolUnidad.objects.filter(activo=True).count()

    # Líderes vigentes (solo cargos marcados como liderazgo)
    lideres_vigentes = UnidadCargo.objects.filter(
        vigente=True,
        rol__tipo=RolUnidad.TIPO_LIDERAZGO

    ).count()

    # Unidades activas / inactivas
    unidades_activas = Unidad.objects.filter(activa=True).count()
    unidades_inactivas = Unidad.objects.filter(activa=False).count()

    # Unidades sin líder vigente (con rol liderazgo)
    unidades_con_lider = UnidadCargo.objects.filter(
        vigente=True,
        rol__tipo=RolUnidad.TIPO_LIDERAZGO

    ).values_list("unidad_id", flat=True).distinct()

    unidades_sin_lider = Unidad.objects.filter(activa=True).exclude(id__in=unidades_con_lider).count()

    # Top unidades por miembros (solo activos)
    top_unidades = (
        Unidad.objects.annotate(
            total_miembros=Count("membresias", filter=Q(membresias__activo=True))
        )
        .order_by("-total_miembros", "nombre")[:6]
    )

    # Distribución por tipo
    distribucion_por_tipo = (
        TipoUnidad.objects.filter(activo=True)
        .annotate(total=Count("unidades"))
        .order_by("orden", "nombre")
    )

    context = {
        "total_unidades": total_unidades,
        "total_tipos": total_tipos,
        "total_roles": total_roles,
        "lideres_vigentes": lideres_vigentes,
        "unidades_activas": unidades_activas,
        "unidades_inactivas": unidades_inactivas,
        "unidades_sin_lider": unidades_sin_lider,
        "top_unidades": top_unidades,
        "distribucion_por_tipo": distribucion_por_tipo,
    }
    return render(request, "estructura_app/dashboard.html", context)


@login_required
def unidad_crear(request):
    if request.method == "POST":
        form = UnidadForm(request.POST)
        if form.is_valid():
            unidad = form.save(commit=False)
            unidad.reglas = _reglas_mvp_from_post(request.POST)
            unidad.save()

            messages.success(request, "Unidad creada correctamente.")

            if request.POST.get("guardar_y_nuevo") == "1":
                return redirect("estructura_app:unidad_crear")

            return redirect("estructura_app:unidad_listado")
        else:
            messages.error(request, "Revisa los campos marcados. Hay errores en el formulario.")
    else:
        form = UnidadForm()

    context = {
        "form": form,
        "modo": "crear",
        "unidad": None,
    }
    return render(request, "estructura_app/unidad_form.html", context)

@login_required
def unidad_editar(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)

    if request.method == "POST":
        form = UnidadForm(request.POST, instance=unidad)
        if form.is_valid():
            form.save()
            messages.success(request, "Cambios guardados correctamente.")
            return redirect("estructura_app:unidad_editar", pk=unidad.pk)
        else:
            messages.error(request, "Revisa los campos marcados. Hay errores en el formulario.")
    else:
        form = UnidadForm(instance=unidad)

    context = {
        "form": form,
        "modo": "editar",
        "unidad": unidad,
    }
    return render(request, "estructura_app/unidad_form.html", context)



def unidad_listado(request):
    query = request.GET.get('q', '').strip()

    unidades = Unidad.objects.all().order_by('nombre')
    if query:
        unidades = unidades.filter(nombre__icontains=query) | unidades.filter(codigo__icontains=query)

    return render(request, 'estructura_app/unidad_listado.html', {
        'unidades': unidades,
        'query': query,
    })

def unidad_detalle(request, pk):
    unidad = get_object_or_404(Unidad, pk=pk)
    return render(request, 'estructura_app/unidad_detalle.html', {'unidad': unidad})

def _reglas_mvp_from_post(post):
    """
    Lee reglas MVP desde request.POST y devuelve un dict listo para guardar en JSONField.
    'solo_activos' por defecto: True.
    Si 'solo_activos' está activo, BLOQUEA (fuerza False) las demás reglas de membresía.
    """
    def is_on(name, default=False):
        if name not in post:
            return default
        return post.get(name) in ("on", "1", "true", "True")

    def to_int(name, default=None):
        raw = (post.get(name) or "").strip()
        if raw == "":
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    solo_activos = is_on("regla_solo_activos", default=True)

    # Reglas secundarias (solo si la maestra está apagada)
    permite_menores = False if solo_activos else is_on("regla_perm_menores", default=False)
    permite_observacion = False if solo_activos else is_on("regla_perm_observacion", default=False)
    permite_nuevos = False if solo_activos else is_on("regla_perm_nuevos", default=False)
    permite_catecumenos = False if solo_activos else is_on("regla_perm_catecumenos", default=False)
    permite_visitantes = False if solo_activos else is_on("regla_perm_visitantes", default=False)

    return {
        # Membresía
        "solo_activos": solo_activos,
        "permite_menores": permite_menores,
        "permite_observacion": permite_observacion,
        "permite_nuevos": permite_nuevos,
        "permite_catecumenos": permite_catecumenos,
        "permite_visitantes": permite_visitantes,

        # Límites / Estructura
        "capacidad_maxima": to_int("regla_capacidad_maxima", default=None),
        "permite_subunidades": is_on("regla_perm_subunidades", default=True),

        # Ingreso
        "requiere_aprobacion_lider": is_on("regla_req_aprob_lider", default=False),

        # Privacidad
        "unidad_privada": is_on("regla_unidad_privada", default=False),
    }

from django.shortcuts import render


@login_required
def asignacion_unidad(request):
    unidades = Unidad.objects.filter(activa=True).order_by("nombre")
    roles = RolUnidad.objects.filter(activo=True).order_by("orden", "nombre")

    # Lista de personas (ajusta filtros si quieres: activos, etc.)
    # NO precargamos personas, se cargan por AJAX cuando elijan unidad
    return render(request, "estructura_app/asignacion_unidad.html", {
        "unidades": unidades,
        "roles": roles,
        "personas": [],
    })

    for p in personas_qs:
        p.estado_slug = _estado_slug(getattr(p, "estado_pastoral", ""))
        personas.append(p)

    if request.method == "POST":
        unidad_id = (request.POST.get("unidad") or "").strip()
        rol_id = (request.POST.get("rol") or "").strip()
        personas_raw = (request.POST.get("personas") or "").strip()

        if not unidad_id or not rol_id or not personas_raw:
            messages.error(request, "Debes seleccionar una unidad, un rol y al menos una persona.")
            return redirect("estructura_app:asignacion_unidad")

        unidad = get_object_or_404(Unidad, pk=unidad_id)
        rol = get_object_or_404(RolUnidad, pk=rol_id)

        ids = [x for x in personas_raw.split(",") if x.strip().isdigit()]
        miembros = Miembro.objects.filter(id__in=ids)

        if not miembros.exists():
            messages.error(request, "No se encontraron personas válidas para asignar.")
            return redirect("estructura_app:asignacion_unidad")

        hoy = timezone.localdate()
        creados = 0

        for m in miembros:
            # REGLA BASE (la que ya definimos): el rol manda el tipo
            # Liderazgo => UnidadCargo
            # Participación/Trabajo => UnidadMembresia
            if rol.tipo == RolUnidad.TIPO_LIDERAZGO:
                # Si ya tiene un liderazgo vigente en ESA unidad con ESE rol, no duplicar
                obj, created = UnidadCargo.objects.get_or_create(
                    miembo_fk=m,
                    unidad=unidad,
                    rol=rol,
                    defaults={"vigente": True, "fecha_inicio": hoy},
                )
                if created:
                    creados += 1

                # Si no existe membresía previa en la unidad, créala automáticamente (como acordamos)
                UnidadMembresia.objects.get_or_create(
                    miembo_fk=m,
                    unidad=unidad,
                    defaults={"activo": True, "tipo": "colaborador", "fecha_ingreso": hoy},
                )

            else:
                # Participación/Trabajo => membresía
                # Aquí el rol no se guarda en UnidadMembresia (tu modelo no tiene FK a rol),
                # así que lo usamos para decidir "tipo"
                tipo_membresia = "miembro" if rol.tipo == RolUnidad.TIPO_PARTICIPACION else "colaborador"

                obj, created = UnidadMembresia.objects.get_or_create(
                    miembo_fk=m,
                    unidad=unidad,
                    defaults={"activo": True, "tipo": tipo_membresia, "fecha_ingreso": hoy},
                )
                if created:
                    creados += 1

        messages.success(request, f"Asignación completada. Nuevos registros creados: {creados}.")
        return redirect("estructura_app:asignacion_unidad")

    return render(
        request,
        "estructura_app/asignacion_unidad.html",
        {
            "unidades": unidades,
            "roles": roles,
            "personas": personas,
        },
    )

@login_required
def rol_listado(request):
    roles = RolUnidad.objects.all().order_by("orden", "nombre")
    return render(
        request,
        "estructura_app/rol_listado.html",
        {
            "roles": roles,
        }
    )

@login_required
def rol_crear(request):
    if request.method == "POST":
        form = RolUnidadForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Rol creado correctamente.")
            return redirect("estructura_app:rol_listado")
    else:
        form = RolUnidadForm()

    return render(
        request,
        "estructura_app/rol_form.html",
        {
            "form": form,
            "modo": "crear",
        }
    )

def _estado_slug(estado):
    if not estado:
        return "vacio"
    s = str(estado).strip().lower()
    s = (s.replace("á", "a").replace("é", "e").replace("í", "i")
           .replace("ó", "o").replace("ú", "u").replace("ñ", "n"))
    return s


@login_required
def asignacion_unidad_contexto(request):
    unidad_id = (request.GET.get("unidad_id") or "").strip()
    if not unidad_id:
        return JsonResponse({"ok": False, "error": "Falta unidad_id"}, status=400)

    unidad = get_object_or_404(Unidad, pk=unidad_id)

    # Miembros actuales (activos) en esta unidad
    miembros_actuales_ids = set(
        UnidadMembresia.objects.filter(unidad=unidad, activo=True)
        .values_list("miembo_fk_id", flat=True)
    )

    # ✅ Candidatos: puedes empezar con TODOS los miembros
    # (luego aplicamos reglas de unidad cuando ya existan en el modelo)
    qs = Miembro.objects.all().order_by("nombres", "apellidos")

    personas = []
    for p in qs:
        estado = getattr(p, "estado_pastoral", "") or ""
        personas.append({
            "id": p.id,
            "nombre": getattr(p, "nombre_completo", str(p)),
            "codigo": getattr(p, "codigo", ""),
            "estado": estado,
            "estado_slug": _estado_slug(estado),
            "ya_en_unidad": p.id in miembros_actuales_ids,
        })

    return JsonResponse({
        "ok": True,
        "unidad": {
            "id": unidad.id,
            "nombre": unidad.nombre,
            "tipo": str(getattr(unidad, "tipo", "")) if getattr(unidad, "tipo", None) else "—",
            "miembros_actuales": len(miembros_actuales_ids),
        },
        "personas": personas,
    })


@login_required
@require_POST
def asignacion_guardar_contexto(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    unidad_id = str(payload.get("unidad_id", "")).strip()
    rol_id = str(payload.get("rol_id", "")).strip()

    if not unidad_id or not rol_id:
        return JsonResponse({"ok": False, "error": "Falta unidad o rol"}, status=400)

    unidad = get_object_or_404(Unidad, pk=unidad_id)
    rol = get_object_or_404(RolUnidad, pk=rol_id)

    # Aquí, por ahora, “guardar” puede ser simplemente validar y devolver OK.
    # Si luego quieres persistirlo, creamos un modelo AsignacionContexto (usuario, unidad, rol, timestamp)
    return JsonResponse({"ok": True})