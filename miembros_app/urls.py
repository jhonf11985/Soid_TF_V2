# -*- coding: utf-8 -*-
"""
miembros_app/urls.py
URLs del módulo de miembros organizadas por sección.
"""
from miembros_app.views.familiares import familias_home, familia_detalle

from django.urls import path
from . import views
from . import views_reportes
from miembros_app.views.familiares import (
    familiares_lista,
    familiares_agregar,
    familiares_editar,
    familiares_eliminar,
    ajax_buscar_miembros,
    ajax_validar_relacion,
)


app_name = "miembros_app"

urlpatterns = [
    # ═══════════════════════════════════════════════════════════════════════════
    # DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════
    path("", views.miembros_dashboard, name="dashboard"),

    # ═══════════════════════════════════════════════════════════════════════════
    # CRUD MIEMBROS
    # ═══════════════════════════════════════════════════════════════════════════
    path("lista/", views.miembro_lista, name="lista"),
    path("crear/", views.miembro_crear, name="crear"),
    path("editar/<int:pk>/", views.MiembroUpdateView.as_view(), name="editar"),
    path("detalle/<int:pk>/", views.MiembroDetailView.as_view(), name="detalle"),
    path("ficha/<int:pk>/", views.miembro_ficha, name="ficha"),

    # ═══════════════════════════════════════════════════════════════════════════
    # FAMILIARES (NUEVO MÓDULO)
    # ═══════════════════════════════════════════════════════════════════════════
    path("<int:pk>/familiares/", familiares_lista, name="familiares_lista"),
    path("<int:pk>/familiares/agregar/", familiares_agregar, name="familiares_agregar"),
    path("<int:pk>/familiares/<int:relacion_id>/editar/", familiares_editar, name="familiares_editar"),
    path("<int:pk>/familiares/<int:relacion_id>/eliminar/", familiares_eliminar, name="familiares_eliminar"),

    # ═══════════════════════════════════════════════════════════════════════════
    # NUEVOS CREYENTES
    # ═══════════════════════════════════════════════════════════════════════════
    path("nuevos-creyentes/", views.nuevo_creyente_lista, name="nuevo_creyente_lista"),
    path("nuevos-creyentes/registrar/", views.nuevo_creyente_crear, name="nuevo_creyente_crear"),
    path("nuevos-creyentes/editar/<int:pk>/", views.nuevo_creyente_editar, name="nuevo_creyente_editar"),
    path("nuevos-creyentes/<int:pk>/", views.nuevo_creyente_detalle, name="nuevo_creyente_detalle"),
    path("nuevos-creyentes/ficha/<int:pk>/", views.nuevo_creyente_ficha, name="nuevo_creyente_ficha"),
    path("miembro/<int:pk>/enviar-nuevo-creyente/", views.enviar_a_nuevo_creyente, name="enviar_a_nuevo_creyente"),

    # ═══════════════════════════════════════════════════════════════════════════
    # SALIDAS / INACTIVOS / REINGRESOS
    # ═══════════════════════════════════════════════════════════════════════════
    path("salida/<int:pk>/", views.miembro_dar_salida, name="miembro_dar_salida"),
    path("miembros/<int:pk>/salida/", views.salida_form, name="salida_form"),
    path("miembros/<int:pk>/nuevo-creyente/salida/", views.nuevo_creyente_dar_salida, name="nuevo_creyente_dar_salida"),
    path("inactivos/<int:pk>/", views.miembro_inactivo_detalle, name="inactivo_detalle"),
    path("inactivos/<int:pk>/reincorporar/", views.reincorporar_miembro, name="reincorporar_miembro"),
    path("cartas/salida/<int:pk>/", views.carta_salida_miembro, name="carta_salida_miembro"),

    # ═══════════════════════════════════════════════════════════════════════════
    # REPORTES
    # ═══════════════════════════════════════════════════════════════════════════
    path("reportes/", views.reportes_miembros, name="reportes_home"),
    path("reportes/listado/", views.reporte_listado_miembros, name="reporte_listado_miembros"),
    path("reportes/cumple-mes/", views.reporte_cumple_mes, name="reporte_cumple_mes"),
    path("reportes/nuevos-mes/", views.reporte_miembros_nuevos_mes, name="reporte_miembros_nuevos_mes"),
    path("reportes/salidas/", views.reporte_miembros_salida, name="reporte_miembros_salida"),
    path("reportes/nuevos-creyentes/", views.reporte_nuevos_creyentes, name="reporte_nuevos_creyentes"),
    path("reportes/relaciones-familiares/", views.reporte_relaciones_familiares, name="reporte_relaciones_familiares"),

    # ═══════════════════════════════════════════════════════════════════════════
    # EXCEL (IMPORTAR / EXPORTAR)
    # ═══════════════════════════════════════════════════════════════════════════
    path("miembros/listado/exportar-excel/", views.exportar_miembros_excel, name="exportar_miembros_excel"),
    path("miembros/listado/importar-excel/", views.importar_miembros_excel, name="importar_miembros_excel"),

    # ═══════════════════════════════════════════════════════════════════════════
    # ENVÍO POR EMAIL
    # ═══════════════════════════════════════════════════════════════════════════
    path("miembro/<int:pk>/enviar-ficha-email/", views.miembro_enviar_ficha_email, name="miembro_enviar_ficha_email"),
    path("miembros/listado/enviar-email/", views.listado_miembros_enviar_email, name="listado_miembros_enviar_email"),
    path("nuevos-creyentes/enviar-email/", views.nuevos_creyentes_enviar_email, name="nuevos_creyentes_enviar_email"),

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPARTIR POR WHATSAPP
    # ═══════════════════════════════════════════════════════════════════════════
    path("miembros/listado/compartir/", views_reportes.compartir_listado_whatsapp, name="listado_miembros_compartir"),

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOQUEO / DESBLOQUEO DE SECCIONES
    # ═══════════════════════════════════════════════════════════════════════════
    path("miembros/<int:pk>/privado/desbloquear/", views.miembro_privado_desbloquear, name="miembro_privado_desbloquear"),
    path("miembros/<int:pk>/privado/bloquear/", views.miembro_privado_bloquear, name="miembro_privado_bloquear"),
    path("miembros/<int:pk>/finanzas/desbloquear/", views.miembro_finanzas_desbloquear, name="miembro_finanzas_desbloquear"),
    path("miembros/<int:pk>/finanzas/bloquear/", views.miembro_finanzas_bloquear, name="miembro_finanzas_bloquear"),

    # ═══════════════════════════════════════════════════════════════════════════
    # AJAX / VALIDACIONES
    # ═══════════════════════════════════════════════════════════════════════════
    path("ajax/validar-cedula/", views.ajax_validar_cedula, name="ajax_validar_cedula"),
    path("ajax/validar-telefono/", views.validar_telefono, name="ajax_validar_telefono"),
    path("ajax/buscar-miembros/", ajax_buscar_miembros, name="ajax_buscar_miembros"),
    path("ajax/validar-relacion/", ajax_validar_relacion, name="ajax_validar_relacion"),

    # ═══════════════════════════════════════════════════════════════════════════
    # BITÁCORA
    # ═══════════════════════════════════════════════════════════════════════════
    path("miembros/<int:pk>/bitacora/add/", views.miembro_bitacora_add, name="bitacora_add"),

    # ═══════════════════════════════════════════════════════════════════════════
    # MAPA
    # ═══════════════════════════════════════════════════════════════════════════
    path("mapa/", views.mapa_miembros, name="mapa_miembros"),
    path("api/mapa-miembros/", views.api_mapa_miembros, name="api_mapa_miembros"),

    # ═══════════════════════════════════════════════════════════════════════════
    # PADRES ESPIRITUALES
    # ═══════════════════════════════════════════════════════════════════════════
    path("miembros/<int:miembro_id>/padre/add/", views.padre_espiritual_add_simple, name="padre_add_simple"),
    path("miembros/<int:miembro_id>/padre/<int:padre_id>/remove/", views.padre_espiritual_remove_simple, name="padre_remove_simple"),
      path("familias/", familias_home, name="familias_home"),
    path("familias/<int:hogar_id>/", familia_detalle, name="familia_detalle"),

]