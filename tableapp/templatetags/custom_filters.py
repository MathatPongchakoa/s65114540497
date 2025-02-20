from django import template

register = template.Library()

@register.filter
def translate_table_status(value):
    status_mapping = {
        'available': 'ว่าง',
        'occupied': 'กำลังนั่ง',
        'booked': 'จอง',
        'pending': 'รอยืนยัน',
        'cancelled': 'ยกเลิก'
    }
    return status_mapping.get(value, value)  # คืนค่าเดิมหากไม่พบในแมป

@register.filter
def to_thai_date(value):
    """Convert a date from AD to BE (พุทธศักราช)."""
    if value:
        return value.strftime('%d/%m/') + str(value.year + 543)
    return ''
