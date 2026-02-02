# -*- coding: utf-8 -*-
"""
miembros_app/views/utils.py
Funciones auxiliares y constantes compartidas entre todas las vistas.
"""

import re
from datetime import date, timedelta
from io import BytesIO

from django.apps import apps
from django.db.models import Q

from core.models import Module


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

CORTE_NINOS = 12  # Edad límite para considerar niños

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

# Tipos de relación por categoría
TIPOS_NUCLEAR = {"conyuge", "hijo"}
TIPOS_ORIGEN = {"padre", "madre", "hermano"}
TIPOS_EXTENDIDA = {"abuelo", "nieto", "tio", "sobrino", "primo", "bisabuelo", "bisnieto"}
TIPOS_POLITICA = {"suegro", "cunado", "yerno", "consuegro"}

# Validación de cédula dominicana
CEDULA_RE = re.compile(r"^\d{3}-\d{7}-\d$")


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES GENERALES
# ═══════════════════════════════════════════════════════════════════════════════

def calcular_edad(fecha_nacimiento, fecha_referencia=None):
    """Calcula la edad a partir de una fecha de nacimiento."""
    if not fecha_nacimiento:
        return None
    
    referencia = fecha_referencia or date.today()
    edad = referencia.year - fecha_nacimiento.year
    
    if (referencia.month, referencia.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    
    return edad


def porcentaje(cantidad, base):
    """Calcula el porcentaje con manejo de división por cero."""
    if base == 0:
        return 0
    return round((cantidad * 100) / base, 1)


def wa_digits(valor):
    """Extrae solo dígitos para URLs de WhatsApp."""
    return "".join(ch for ch in (valor or "") if ch.isdigit())


def _safe_get_model(app_label, model_name):
    """Obtiene un modelo de forma segura, retornando None si no existe."""
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None


def get_choices_safe(model, field_name):
    """Obtiene las choices de un campo de forma segura."""
    try:
        campo = model._meta.get_field(field_name)
        return list(campo.flatchoices)
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DE MÓDULOS
# ═══════════════════════════════════════════════════════════════════════════════

def modulo_estructura_activo():
    """Verifica si el módulo de estructura está activo."""
    return Module.objects.filter(
        is_enabled=True,
        code__in=["Estructura", "Unidad", "Unidades"]
    ).exists()


def modulo_nuevo_creyente_activo():
    """Verifica si el módulo de nuevo creyente está activo."""
    return Module.objects.filter(
        is_enabled=True,
        code="nuevo_creyente"
    ).exists()


def miembro_tiene_asignacion_en_unidades(miembro_obj):
    """
    True si el miembro está asignado a alguna unidad (UnidadCargo o UnidadMembresia).
    """
    from miembros_app.models import Miembro
    
    if not modulo_estructura_activo():
        return False

    modelos = ("UnidadMembresia", "UnidadCargo")

    for model_name in modelos:
        Modelo = _safe_get_model("estructura_app", model_name)
        if not Modelo:
            continue

        # Detectar el FK a Miembro
        fk_name = None
        for f in Modelo._meta.fields:
            if getattr(f, "remote_field", None) and f.remote_field and f.remote_field.model == Miembro:
                fk_name = f.name
                break

        if not fk_name:
            continue

        qs = Modelo.objects.filter(**{fk_name: miembro_obj})

        # Filtrar por vigentes si existe el campo
        for end_field in ("fecha_fin", "fecha_final", "fecha_hasta", "fecha_salida"):
            if hasattr(Modelo, end_field):
                qs = qs.filter(**{f"{end_field}__isnull": True})
                break

        if hasattr(Modelo, "activo"):
            qs = qs.filter(activo=True)

        if qs.exists():
            return True

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# PDF
# ═══════════════════════════════════════════════════════════════════════════════

def generar_pdf_desde_html(html_string):
    """Genera PDF desde HTML usando xhtml2pdf."""
    from xhtml2pdf import pisa
    
    result = BytesIO()
    status = pisa.CreatePDF(html_string, dest=result)
    
    if status.err:
        raise Exception("xhtml2pdf no pudo generar el PDF")
    
    return result.getvalue()