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


]

