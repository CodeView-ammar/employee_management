from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """ضرب قيمتين"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """قسمة قيمتين"""
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """حساب النسبة المئوية"""
    try:
        return round((float(value) / float(total)) * 100, 2) if float(total) != 0 else 0
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    """طرح قيمتين"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def add_filter(value, arg):
    """جمع قيمتين"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0