from django import template
import math

register = template.Library()

@register.filter
def to_radian(value):
    """Convert degrees to radians."""
    return math.radians(value)

@register.filter
def to_thai_date(value):
    """Convert a date from AD to BE (พุทธศักราช)."""
    if value:
        return value.strftime('%d/%m/') + str(value.year + 543)
    return ''
