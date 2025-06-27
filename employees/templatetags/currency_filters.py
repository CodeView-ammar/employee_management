
from django import template
from decimal import Decimal
import locale

register = template.Library()

@register.filter
def currency(value):
    """تنسيق المبلغ مع الفواصل"""
    try:
        if value is None:
            return '0.00'
        
        # تحويل إلى Decimal للتأكد من الدقة
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif isinstance(value, str):
            value = Decimal(value)
        
        # تنسيق الرقم مع الفواصل
        formatted = "{:,.2f}".format(float(value))
        return formatted
        
    except (ValueError, TypeError, Exception):
        return '0.00'

@register.filter
def currency_no_decimal(value):
    """تنسيق المبلغ مع الفواصل بدون خانات عشرية"""
    try:
        if value is None:
            return '0'
        
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif isinstance(value, str):
            value = Decimal(value)
        
        # تنسيق الرقم مع الفواصل بدون خانات عشرية
        formatted = "{:,.0f}".format(float(value))
        return formatted
        
    except (ValueError, TypeError, Exception):
        return '0'

@register.filter
def percentage(value, decimal_places=2):
    """تنسيق النسبة المئوية"""
    try:
        if value is None:
            return '0%'
        
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif isinstance(value, str):
            value = Decimal(value)
        
        formatted = "{:.{}f}%".format(float(value), decimal_places)
        return formatted
        
    except (ValueError, TypeError, Exception):
        return '0%'

@register.filter
def sar_currency(value):
    """تنسيق المبلغ مع عملة الريال السعودي"""
    formatted_value = currency(value)
    return f"{formatted_value} ريال"
