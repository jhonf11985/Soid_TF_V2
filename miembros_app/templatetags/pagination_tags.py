# -*- coding: utf-8 -*-
"""
miembros_app/templatetags/pagination_tags.py
Template tags para paginación con filtros.
"""

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, field, value):
    """
    Reemplaza un parámetro GET manteniendo los demás.
    Uso: {% url_replace 'page' 2 %}
    """
    request = context.get('request')
    if not request:
        return ''
    
    query = request.GET.copy()
    query[field] = value
    return query.urlencode()


@register.simple_tag(takes_context=True)
def query_string(context, **kwargs):
    """
    Genera query string manteniendo parámetros actuales y sobrescribiendo los dados.
    Uso: {% query_string page=2 %}
    """
    request = context.get('request')
    if not request:
        return ''
    
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = value
    
    return query.urlencode()