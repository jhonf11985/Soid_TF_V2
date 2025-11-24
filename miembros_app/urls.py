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
]
