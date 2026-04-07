# -*- coding: utf-8 -*-
"""
miembros_app/templatetags/miembros_extras.py

Template tags adicionales para miembros_app.
Si ya existe este archivo, agregar solo el filtro get_item.
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Obtiene un valor de un diccionario por clave.
    Uso: {{ mi_dict|get_item:clave }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)