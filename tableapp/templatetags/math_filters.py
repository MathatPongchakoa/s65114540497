from django import template

register = template.Library()

@register.filter
def add(value, arg):
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return value  # ส่งคืนค่าเดิมหากมีข้อผิดพลาด

@register.filter
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value
