# -*- coding: utf-8 -*-
"""
miembros_app/views/__init__.py
Exporta todas las vistas para mantener compatibilidad con urls.py existente.
"""

# Dashboard
from .dashboard import miembros_dashboard

# CRUD de Miembros
from .miembros import (
    miembro_lista,
    miembro_lista_pdf,
    miembro_crear,
    MiembroUpdateView,
    MiembroDetailView,
    miembro_ficha,
    filtrar_miembros,
)

# Familiares
from .familiares import (
    agregar_familiar,
    eliminar_familiar,
    calcular_parentescos_inferidos,
    obtener_relaciones_organizadas,
    obtener_familia_completa,
)

# API / JSON
from .api import (
    miembro_finanzas_desbloquear,
    miembro_finanzas_bloquear,
    miembro_privado_desbloquear,
    miembro_privado_bloquear,
    ajax_validar_cedula,
    listado_miembros_crear_link_publico,
)

# Nuevos Creyentes
from .nuevos_creyentes import (
    nuevo_creyente_crear,
    nuevo_creyente_lista,
    nuevo_creyente_editar,
    nuevo_creyente_detalle,
    nuevo_creyente_ficha,
    enviar_a_nuevo_creyente,
)

# Inactivos / Salidas / Reingresos
from .inactivos import (
    miembro_inactivo_detalle,
    salida_form,
    miembro_dar_salida,
    nuevo_creyente_dar_salida,
    reincorporar_miembro,
    carta_salida_miembro,
)

# Reportes
from .reportes import (
    reportes_miembros,
    reporte_listado_miembros,
    reporte_cumple_mes,
    reporte_miembros_nuevos_mes,
    reporte_miembros_salida,
    reporte_nuevos_creyentes,
    reporte_relaciones_familiares,
    exportar_miembros_excel,
    importar_miembros_excel,
    listado_miembros_enviar_email,
)

# Extras (mapa, bitácora, padres espirituales, emails)
from .extras import (
    validar_telefono,
    mapa_miembros,
    api_mapa_miembros,
    miembro_bitacora_add,
    padre_espiritual_add_simple,
    padre_espiritual_remove_simple,
    miembro_enviar_ficha_email,
    nuevos_creyentes_enviar_email,
)

# Utils (para uso interno)
from .utils import (
    calcular_edad,
    porcentaje,
    wa_digits,
    modulo_estructura_activo,
    modulo_nuevo_creyente_activo,
    miembro_tiene_asignacion_en_unidades,
    generar_pdf_desde_html,
    get_choices_safe,
    MESES_ES,
    CORTE_NINOS,
    TIPOS_NUCLEAR,
    TIPOS_ORIGEN,
    TIPOS_EXTENDIDA,
    TIPOS_POLITICA,
)