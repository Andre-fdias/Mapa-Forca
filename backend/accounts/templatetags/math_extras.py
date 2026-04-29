from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtrai o argumento do valor."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0
