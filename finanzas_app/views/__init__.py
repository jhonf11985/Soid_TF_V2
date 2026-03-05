from .dashboard import dashboard, egreso_recibo
from .cuentas import cuentas_listado, cuenta_crear, cuenta_editar, cuenta_toggle
from .categorias import categorias_listado, categoria_crear, categoria_editar, categoria_toggle, categoria_sugerir_codigo
from .movimientos import movimientos_listado, movimiento_crear, ingreso_crear, egreso_crear, movimiento_editar, movimiento_anular, ingreso_detalle, egreso_detalle, buscar_miembros_finanzas, movimientos_listado_print, ingreso_recibo, ingreso_general_pdf
from .transferencias import transferencia_crear, transferencia_detalle, transferencia_anular, transferencia_general_pdf
from .adjuntos import subir_adjunto, eliminar_adjunto, descargar_adjunto, listar_adjuntos
from .proveedores import proveedores_list, proveedores_create, proveedores_editar
from .cxp import cxp_list, cxp_create, cxp_detail, cxp_edit, cxp_pagar
from .reportes import reportes_home, reporte_resumen_mensual, reporte_resumen_por_cuenta, reporte_resumen_por_categoria, reporte_movimientos_anulados, reporte_transferencias, reporte_cxp, reporte_cxp_por_proveedor, reporte_cxp_vencidas, reporte_antiguedad_cxp, reporte_pagos_cxp, reporte_estado_resultados, reporte_ingresos_por_unidad, reporte_movimientos_unidad, reporte_f001_concilio, reporte_comparativo_anual