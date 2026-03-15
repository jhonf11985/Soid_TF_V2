from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from estructura_app.forms import UnidadForm
from estructura_app.models import Unidad, RolUnidad
from estructura_app.view_helpers.common import _require_tenant
from estructura_app.view_helpers.unidad_helpers import (
    _to_int_from_post,
    _reglas_mvp_from_post,
)
from estructura_app.view_helpers.autosync import _sincronizar_membresias_automaticas


@login_required
@permission_required("estructura_app.add_unidad", raise_exception=True)
def unidad_crear(request):
    tenant = _require_tenant(request)

    if request.method == "POST":
        form = UnidadForm(request.POST, request.FILES)
        if form.is_valid():
            unidad = form.save(commit=False)
            unidad.tenant = tenant
            unidad.edad_min = _to_int_from_post(request.POST, "edad_min")
            unidad.edad_max = _to_int_from_post(request.POST, "edad_max")
            unidad.reglas = _reglas_mvp_from_post(request.POST)

            asignacion_automatica = bool(unidad.reglas.get("asignacion_automatica"))

            if asignacion_automatica:
                existe_rol_base = RolUnidad.objects.filter(
                    tenant=tenant,
                    tipo=RolUnidad.TIPO_PARTICIPACION
                ).exists()

                if not existe_rol_base:
                    messages.error(
                        request,
                        "Para activar la asignación automática, primero debes crear el rol base de participación del sistema."
                    )
                    return render(request, "estructura_app/unidad_form.html", {
                        "form": form,
                        "modo": "crear",
                        "unidad": None,
                        "reglas": unidad.reglas,
                    })

            unidad.save()

            sync = _sincronizar_membresias_automaticas(unidad, tenant)

            if unidad.reglas.get("asignacion_automatica"):
                messages.success(
                    request,
                    f"Unidad creada correctamente. Autoasignación aplicada: "
                    f"{sync['creados']} creados, {sync['reactivados']} reactivados, {sync['desactivados']} desactivados."
                )
            else:
                messages.success(request, "Unidad creada correctamente.")

            if request.POST.get("guardar_y_nuevo") == "1":
                return redirect("estructura_app:unidad_crear")

            return redirect("estructura_app:unidad_listado")
        else:
            messages.error(request, "Revisa los campos marcados. Hay errores en el formulario.")
    else:
        form = UnidadForm()

    return render(request, "estructura_app/unidad_form.html", {
        "form": form,
        "modo": "crear",
        "unidad": None,
        "reglas": {},
    })


@login_required
@permission_required("estructura_app.change_unidad", raise_exception=True)
def unidad_editar(request, pk):
    tenant = _require_tenant(request)
    unidad = get_object_or_404(Unidad, pk=pk, tenant=tenant)
    bloqueada = unidad.esta_bloqueada

    if request.method == "POST":
        if bloqueada:
            imagen = request.FILES.get("imagen")
            if imagen:
                unidad.imagen = imagen
                unidad.save(update_fields=["imagen", "actualizado_en"])
                messages.success(request, "Imagen actualizada correctamente.")
            else:
                messages.warning(request, "No se seleccionó ninguna imagen.")
            return redirect("estructura_app:unidad_editar", pk=unidad.pk)

        form = UnidadForm(request.POST, request.FILES, instance=unidad)
        if form.is_valid():
            unidad_obj = form.save(commit=False)
            unidad_obj.edad_min = _to_int_from_post(request.POST, "edad_min")
            unidad_obj.edad_max = _to_int_from_post(request.POST, "edad_max")

            modo_asignacion = (request.POST.get("modo_asignacion") or "").strip()
            if modo_asignacion in [Unidad.MODO_MANUAL, Unidad.MODO_AUTOMATICA]:
                unidad_obj.modo_asignacion = modo_asignacion

            unidad_obj.reglas = _reglas_mvp_from_post(
                request.POST,
                base_reglas=(unidad.reglas or {})
            )

            asignacion_automatica = bool(unidad_obj.reglas.get("asignacion_automatica"))

            if asignacion_automatica:
                existe_rol_base = RolUnidad.objects.filter(
                    tenant=tenant,
                    tipo=RolUnidad.TIPO_PARTICIPACION
                ).exists()

                if not existe_rol_base:
                    messages.error(
                        request,
                        "Para activar la asignación automática, primero debes crear el rol base de participación del sistema."
                    )
                    return render(request, "estructura_app/unidad_form.html", {
                        "form": form,
                        "modo": "editar",
                        "unidad": unidad,
                        "bloqueada": bloqueada,
                        "reglas": unidad_obj.reglas,
                    })

            unidad_obj.save()

            sync = _sincronizar_membresias_automaticas(unidad_obj, tenant)

            if unidad_obj.reglas.get("asignacion_automatica"):
                messages.success(
                    request,
                    f"Cambios guardados correctamente. Autoasignación aplicada: "
                    f"{sync['creados']} creados, {sync['reactivados']} reactivados, {sync['desactivados']} desactivados."
                )
            else:
                messages.success(request, "Cambios guardados correctamente.")

            return redirect("estructura_app:unidad_listado")
        else:
            messages.error(request, "Revisa los campos marcados.")
    else:
        form = UnidadForm(instance=unidad)

    if bloqueada:
        messages.warning(
            request,
            "Esta unidad ya tiene miembros o cargos asignados. Solo puedes cambiar la imagen."
        )

    return render(request, "estructura_app/unidad_form.html", {
        "form": form,
        "modo": "editar",
        "unidad": unidad,
        "bloqueada": bloqueada,
        "reglas": unidad.reglas or {},
    })