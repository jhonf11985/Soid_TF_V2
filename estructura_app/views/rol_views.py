from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError
from django.shortcuts import redirect, render, get_object_or_404

from estructura_app.forms import RolUnidadForm
from estructura_app.models import RolUnidad
from estructura_app.view_helpers.common import _rol_en_uso, _require_tenant


@login_required
@permission_required("estructura_app.view_rolunidad", raise_exception=True)
def rol_listado(request):
    tenant = _require_tenant(request)
    roles = RolUnidad.objects.filter(tenant=tenant).order_by("orden", "nombre")

    for r in roles:
        r.en_uso = _rol_en_uso(r, tenant)

    return render(request, "estructura_app/rol_listado.html", {
        "roles": roles
    })


@login_required
@permission_required("estructura_app.add_rolunidad", raise_exception=True)
def rol_crear(request):
    tenant = _require_tenant(request)

    if request.method == "POST":
        form = RolUnidadForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data.get("tipo")
            nombre = (form.cleaned_data.get("nombre") or "").strip()

            ya_existe_nombre = RolUnidad.objects.filter(
                tenant=tenant,
                nombre__iexact=nombre
            ).exists()

            if ya_existe_nombre:
                form.add_error(
                    "nombre",
                    "Ya existe un rol con ese nombre en este tenant."
                )
            elif tipo == RolUnidad.TIPO_PARTICIPACION:
                ya_existe = RolUnidad.objects.filter(
                    tenant=tenant,
                    tipo=RolUnidad.TIPO_PARTICIPACION
                ).exists()

                if ya_existe:
                    mensaje_error = (
                        "No se pudo guardar el rol porque ya existe el rol base de participación "
                        "del sistema. No se permite crear más de uno."
                    )
                    form.add_error("tipo", mensaje_error)
                    messages.error(request, mensaje_error)
                else:
                    rol = form.save(commit=False)
                    rol.tenant = tenant
                    rol.nombre = nombre

                    try:
                        rol.save()
                        messages.success(request, "Rol creado correctamente.")
                        return redirect("estructura_app:rol_listado")
                    except IntegrityError:
                        form.add_error(
                            "nombre",
                            "Ya existe un rol con ese nombre en este tenant."
                        )
            else:
                rol = form.save(commit=False)
                rol.tenant = tenant
                rol.nombre = nombre

                try:
                    rol.save()
                    messages.success(request, "Rol creado correctamente.")
                    return redirect("estructura_app:rol_listado")
                except IntegrityError:
                    form.add_error(
                        "nombre",
                        "Ya existe un rol con ese nombre en este tenant."
                    )
    else:
        form = RolUnidadForm()

    return render(request, "estructura_app/rol_form.html", {
        "form": form,
        "modo": "crear",
    })


@login_required
@permission_required("estructura_app.change_rolunidad", raise_exception=True)
def rol_editar(request, rol_id):
    tenant = _require_tenant(request)
    rol = get_object_or_404(RolUnidad, pk=rol_id, tenant=tenant)

    if request.method == "POST":
        form = RolUnidadForm(request.POST, instance=rol)
        if form.is_valid():
            tipo_nuevo = form.cleaned_data.get("tipo")
            nombre = (form.cleaned_data.get("nombre") or "").strip()

            ya_existe_nombre = (
                RolUnidad.objects
                .filter(tenant=tenant, nombre__iexact=nombre)
                .exclude(pk=rol.pk)
                .exists()
            )

            if ya_existe_nombre:
                form.add_error(
                    "nombre",
                    "Ya existe un rol con ese nombre en este tenant."
                )
            elif tipo_nuevo == RolUnidad.TIPO_PARTICIPACION:
                ya_existe = (
                    RolUnidad.objects
                    .filter(tenant=tenant, tipo=RolUnidad.TIPO_PARTICIPACION)
                    .exclude(pk=rol.pk)
                    .exists()
                )

                if ya_existe:
                    mensaje_error = (
                        "No se pudo guardar el rol porque ya existe el rol base de participación "
                        "del sistema. No se permite crear más de uno."
                    )
                    form.add_error("tipo", mensaje_error)
                    messages.error(request, mensaje_error)
                else:
                    rol_obj = form.save(commit=False)
                    rol_obj.nombre = nombre

                    try:
                        rol_obj.save()
                        messages.success(request, "Rol actualizado correctamente.")
                        return redirect("estructura_app:rol_listado")
                    except IntegrityError:
                        form.add_error(
                            "nombre",
                            "Ya existe un rol con ese nombre en este tenant."
                        )
            else:
                rol_obj = form.save(commit=False)
                rol_obj.nombre = nombre

                try:
                    rol_obj.save()
                    messages.success(request, "Rol actualizado correctamente.")
                    return redirect("estructura_app:rol_listado")
                except IntegrityError:
                    form.add_error(
                        "nombre",
                        "Ya existe un rol con ese nombre en este tenant."
                    )
    else:
        form = RolUnidadForm(instance=rol)

    return render(request, "estructura_app/rol_form.html", {
        "form": form,
        "modo": "editar",
        "rol": rol,
    })