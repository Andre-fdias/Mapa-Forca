from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtrai o argumento do valor."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calcula a porcentagem de value em relação ao total."""
    try:
        if not total or float(total) == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError):
        return 0
