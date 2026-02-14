# -*- coding: utf-8 -*-
"""
miembros_app/validators/__init__.py

Paquete de validadores centralizados.
"""

from .relaciones import (
    ValidadorRelacionFamiliar,
    validar_relacion_familiar,
)

__all__ = [
    "ValidadorRelacionFamiliar",
    "validar_relacion_familiar",
]