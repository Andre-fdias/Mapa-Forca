import re
from django import template

register = library = template.Library()

@register.filter
def extract_user_id(value):
    """Extrai o ID do usuário da string '... ID:123'"""
    match = re.search(r'ID:(\d+)', str(value))
    return match.group(1) if match else None

@register.filter
def clean_notification_msg(value):
    """Remove o sufixo 'Caso queira aprovar agora click aqui ID:X' da mensagem."""
    return re.sub(r'Caso queira aprovar agora click aqui ID:\d+', '', str(value)).strip()
