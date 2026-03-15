from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
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

            if tipo == RolUnidad.TIPO_PARTICIPACION:
                ya_existe = RolUnidad.objects.filter(
                    tenant=tenant,
                    tipo=RolUnidad.TIPO_PARTICIPACION
                ).exists()

                if ya_existe:
                    form.add_error(
                        "tipo",
                        "Ya existe el rol base de participación del sistema. No se permite crear más de uno."
                    )
                else:
                    rol = form.save(commit=False)
                    rol.tenant = tenant
                    rol.save()
                    messages.success(request, "Rol creado correctamente.")
                    return redirect("estructura_app:rol_listado")
            else:
                rol = form.save(commit=False)
                rol.tenant = tenant
                rol.save()
                messages.success(request, "Rol creado correctamente.")
                return redirect("estructura_app:rol_listado")
    else:
        form = RolUnidadForm()

    return render(request, "estructura_app/rol_form.html", {
        "form": form,
        "modo": "crear",
    })


@login_required
@permission_required("estructura_app.change_rolunidad", raise_exception=True)
def rol_editar(request, pk):
    tenant = _require_tenant(request)
    rol = get_object_or_404(RolUnidad, pk=pk, tenant=tenant)

    if request.method == "POST":
        form = RolUnidadForm(request.POST, instance=rol)
        if form.is_valid():
            tipo_nuevo = form.cleaned_data.get("tipo")

            if tipo_nuevo == RolUnidad.TIPO_PARTICIPACION:
                ya_existe = (
                    RolUnidad.objects
                    .filter(tenant=tenant, tipo=RolUnidad.TIPO_PARTICIPACION)
                    .exclude(pk=rol.pk)
                    .exists()
                )

                if ya_existe:
                    form.add_error(
                        "tipo",
                        "Ya existe el rol base de participación del sistema. No se permite crear más de uno."
                    )
                else:
                    form.save()
                    messages.success(request, "Rol actualizado correctamente.")
                    return redirect("estructura_app:rol_listado")
            else:
                form.save()
                messages.success(request, "Rol actualizado correctamente.")
                return redirect("estructura_app:rol_listado")
    else:
        form = RolUnidadForm(instance=rol)

    return render(request, "estructura_app/rol_form.html", {
        "form": form,
        "modo": "editar",
        "rol": rol,
    })