# finanzas_app/urls.py

from django.urls import path
from . import views

app_name = "finanzas_app"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    
    # Cuentas financieras
    path("cuentas/", views.cuentas_listado, name="cuentas_listado"),
    path("cuentas/nueva/", views.cuenta_crear, name="cuenta_crear"),
    path("cuentas/<int:pk>/editar/", views.cuenta_editar, name="cuenta_editar"),
    path("cuentas/<int:pk>/toggle/", views.cuenta_toggle, name="cuenta_toggle"),
    
    # Categorías de movimiento
    path("categorias/", views.categorias_listado, name="categorias_listado"),
    path("categorias/nueva/", views.categoria_crear, name="categoria_crear"),
    path("categorias/<int:pk>/editar/", views.categoria_editar, name="categoria_editar"),
    path("categorias/<int:pk>/toggle/", views.categoria_toggle, name="categoria_toggle"),
    
    # Movimientos
    path("movimientos/", views.movimientos_listado, name="movimientos_listado"),
    path("movimientos/nuevo/", views.movimiento_crear, name="movimiento_crear"),
    path("movimientos/<int:pk>/editar/", views.movimiento_editar, name="movimiento_editar"),
    path("movimientos/<int:pk>/anular/", views.movimiento_anular, name="movimiento_anular"),
    
    # Ingresos (formulario especializado)
    path("ingresos/nuevo/", views.ingreso_crear, name="ingreso_crear"),
    # Egresos (formulario especializado)
    path("egresos/nuevo/", views.egreso_crear, name="egreso_crear"),
    # 👉 NUEVA RUTA PARA DETALLE DE INGRESO
    path("ingresos/<int:pk>/detalle/", views.ingreso_detalle, name="ingreso_detalle"),
        path(
        "miembros/buscar/",
        views.buscar_miembros_finanzas,
        name="buscar_miembros_finanzas",
    ),
    # Transferencias
    path("transferencias/nueva/", views.transferencia_crear, name="transferencia_crear"),
    path("transferencias/<int:pk>/detalle/", views.transferencia_detalle, name="transferencia_detalle"),
    path("transferencias/<int:pk>/anular/", views.transferencia_anular, name="transferencia_anular"),
    # Adjuntos
    path("adjuntos/movimiento/<int:movimiento_id>/subir/", views.subir_adjunto, name="subir_adjunto"),
    path("adjuntos/<int:adjunto_id>/eliminar/", views.eliminar_adjunto, name="eliminar_adjunto"),
    path("adjuntos/<int:adjunto_id>/descargar/", views.descargar_adjunto, name="descargar_adjunto"),
    path("adjuntos/movimiento/<int:movimiento_id>/listar/", views.listar_adjuntos, name="listar_adjuntos"),

    path("ingresos/<int:pk>/recibo/", views.ingreso_recibo, name="ingreso_recibo"),
     path("ingresos/<int:pk>/general-pdf/", views.ingreso_general_pdf, name="ingreso_general_pdf"),
     path(
    "transferencias/<int:pk>/general-pdf/",
    views.transferencia_general_pdf,
    name="transferencia_general_pdf"
    ),
    path("egresos/<int:pk>/", views.egreso_detalle, name="egreso_detalle"),

    path("movimientos/imprimir/", views.movimientos_listado_print, name="movimientos_listado_print"),

path("reportes/resumen-mensual/", views.reporte_resumen_mensual, name="reporte_resumen_mensual"),
# Reportes (HOME)
path("reportes/", views.reportes_home, name="reportes_home"),
path("reportes/resumen-por-cuenta/", views.reporte_resumen_por_cuenta, name="reporte_resumen_por_cuenta"),
path("reportes/resumen-por-categoria/", views.reporte_resumen_por_categoria, name="reporte_resumen_por_categoria"),
path("reportes/anulados/", views.reporte_movimientos_anulados, name="reporte_movimientos_anulados"),
path(
    "reportes/transferencias/",
    views.reporte_transferencias,
    name="reporte_transferencias",
),
 path("egresos/<int:pk>/recibo/", views.egreso_recibo, name="egreso_recibo"),
     path(
        "cuentas-por-pagar/",
        views.cxp_list,
        name="cxp_list",
    ),
    path(
        "cuentas-por-pagar/nueva/",
        views.cxp_create,
        name="cxp_create",
    ),
    path(
        "cuentas-por-pagar/<int:pk>/",
        views.cxp_detail,
        name="cxp_detail",
    ),


# Proveedores (CxP)
path("proveedores/", views.proveedores_list, name="proveedores_list"),
path("proveedores/nuevo/", views.proveedores_create, name="proveedores_create"),
path("finanzas/proveedores/<int:pk>/editar/", views.proveedores_editar, name="proveedores_editar"),
path(
    "cuentas-por-pagar/<int:pk>/editar/",
    views.cxp_edit,
    name="cxp_edit",
),
path("cuentas-por-pagar/<int:pk>/pagar/", views.cxp_pagar, name="cxp_pagar"),

]