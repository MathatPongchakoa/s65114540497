from django import template
import math

register = template.Library()

@register.filter
def to_radian(value):
    """Convert degrees to radians."""
    return math.radians(value)

