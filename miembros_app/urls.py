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

]
