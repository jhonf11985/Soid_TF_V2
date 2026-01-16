from django.urls import path
from . import views

app_name = "miembros_app"

urlpatterns = [
    # Panel principal
    path("", views.miembros_dashboard, name="dashboard"),

    # Lista y CRUD
    path("lista/", views.miembro_lista, name="lista"),
    path("crear/", views.miembro_crear, name="crear"),
    path("editar/<int:pk>/", views.MiembroUpdateView.as_view(), name="editar"),
    path("detalle/<int:pk>/", views.MiembroDetailView.as_view(), name="detalle"),

    # 🔹 Reportes
    path("reportes/", views.reportes_miembros, name="reportes_home"),
    path("reportes/listado/", views.reporte_listado_miembros, name="reporte_listado_miembros"),
    path("ficha/<int:pk>/", views.miembro_ficha, name="ficha"),

    # Familiares
    path("<int:pk>/familiares/agregar/", views.agregar_familiar, name="agregar_familiar"),
    path(
        "miembros/familiares/<int:relacion_id>/eliminar/",
        views.eliminar_familiar,
        name="eliminar_familiar",
    ),
    path(
    "reportes/salidas/",
    views.reporte_miembros_salida,
    name="reporte_miembros_salida",
    ),
    path(
    "reportes/relaciones-familiares/",
    views.reporte_relaciones_familiares,
    name="reporte_relaciones_familiares",
        ),
    path(
    "reportes/cumple-mes/",
    views.reporte_cumple_mes,
    name="reporte_cumple_mes",
),
    path(
        "reportes/nuevos-mes/",
        views.reporte_miembros_nuevos_mes,
        name="reporte_miembros_nuevos_mes",
    ),

    path(
        "cartas/salida/<int:pk>/",
        views.carta_salida_miembro,
        name="carta_salida_miembro",
    ),
    # Nuevos creyentes
    path(
        "nuevos-creyentes/",
        views.nuevo_creyente_lista,
        name="nuevo_creyente_lista",
    ),
    path(
        "nuevos-creyentes/registrar/",
        views.nuevo_creyente_crear,
        name="nuevo_creyente_crear",
    ),
    path(
        "nuevos-creyentes/editar/<int:pk>/",
        views.nuevo_creyente_editar,
        name="nuevo_creyente_editar",
    ),
    path(
    "reportes/nuevos-creyentes/",
    views.reporte_nuevos_creyentes,
    name="reporte_nuevos_creyentes"
),

path(
    "nuevos-creyentes/ficha/<int:pk>/",
    views.nuevo_creyente_ficha,
    name="nuevo_creyente_ficha"
),
    path(
        "miembro/<int:pk>/enviar-ficha-email/",
        views.miembro_enviar_ficha_email,
        name="miembro_enviar_ficha_email",
    ),
 path(
        "miembros/listado/enviar-email/",
        views.listado_miembros_enviar_email,
        name="listado_miembros_enviar_email",
    ),
    path(
    "miembros/listado/enviar-email/",
    views.listado_miembros_enviar_email,
    name="listado_miembros_enviar_email",
),

    path(
        "nuevos-creyentes/enviar-email/",
        views.nuevos_creyentes_enviar_email,
        name="nuevos_creyentes_enviar_email",
    ),
        path(
        "miembros/listado/exportar-excel/",
        views.exportar_miembros_excel,
        name="exportar_miembros_excel",
    ),
    path(
        "miembros/listado/importar-excel/",
        views.importar_miembros_excel,
        name="importar_miembros_excel",
    ),
path(
    "miembro/<int:pk>/enviar-nuevo-creyente/",
    views.enviar_a_nuevo_creyente,
    name="enviar_a_nuevo_creyente",
),

    path("salida/<int:pk>/", views.miembro_dar_salida, name="miembro_dar_salida"),

    path("miembros/<int:pk>/privado/desbloquear/", views.miembro_privado_desbloquear, name="miembro_privado_desbloquear"),
    path("miembros/<int:pk>/privado/bloquear/", views.miembro_privado_bloquear, name="miembro_privado_bloquear"),

path("miembros/<int:pk>/finanzas/desbloquear/", views.miembro_finanzas_desbloquear, name="miembro_finanzas_desbloquear"),
path("miembros/<int:pk>/finanzas/bloquear/", views.miembro_finanzas_bloquear, name="miembro_finanzas_bloquear"),

  path("ajax/validar-cedula/", views.ajax_validar_cedula, name="ajax_validar_cedula"),
  path(
    "miembros/<int:pk>/nuevo-creyente/salida/",
    views.nuevo_creyente_dar_salida,
    name="nuevo_creyente_dar_salida",
),
  path("nuevos-creyentes/<int:pk>/", views.nuevo_creyente_detalle, name="nuevo_creyente_detalle"),
path("inactivos/<int:pk>/", views.miembro_inactivo_detalle, name="inactivo_detalle"),




path("inactivos/<int:pk>/reincorporar/", views.reincorporar_miembro, name="reincorporar_miembro"),

    path(
        "miembros/<int:pk>/salida/",
        views.salida_form,
        name="salida_form"
    ),

    path('miembros/<int:pk>/bitacora/add/', views.miembro_bitacora_add, name='bitacora_add'),
    path(
    "ajax/validar-telefono/",
    views.validar_telefono,
    name="ajax_validar_telefono"
),
path("ajax/validar-telefono/", views.validar_telefono, name="validar_telefono"),

    path("mapa/", views.mapa_miembros, name="mapa_miembros"),
    path("api/mapa-miembros/", views.api_mapa_miembros, name="api_mapa_miembros"),

path("miembros/<int:miembro_id>/padre/add/", views.padre_espiritual_add_simple, name="padre_add_simple"),
path("miembros/<int:miembro_id>/padre/<int:padre_id>/remove/", views.padre_espiritual_remove_simple, name="padre_remove_simple"),

]

