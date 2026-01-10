"""
filtres personnalises pour les templates
"""

from django import template

register = template.Library()

@register.filter
def get_id(movie):
    """recupere l id mongodb en contournant la restriction underscore"""
    if isinstance(movie, dict):
        return movie.get('_id', '')
    return getattr(movie, '_id', '')
