from .models import Notification
from tickets.models import Ticket

def notification_context(request):
    if request.user.is_authenticated:
        # Notificações para o sininho (não lidas)
        unread_notifications = Notification.objects.filter(user=request.user, lida=False)
        
        # Notificações para o modal central (não exibidas)
        pending_modal_notifications = Notification.objects.filter(user=request.user, exibida_em_modal=False)
        
        # Chamados (Tickets) não lidos
        user = request.user
        is_support = user.is_superuser or user.role in ['ADMIN', 'COBOM']
        
        if is_support:
            # Suporte: conta chamados ABERTOS não lidos por ele
            unread_tickets_count = Ticket.objects.filter(status='ABERTO', lido_pelo_suporte=False).count()
        else:
            # User: conta seus chamados ABERTOS não lidos por ele
            unread_tickets_count = Ticket.objects.filter(requisitante=user, status='ABERTO', lido_pelo_requisitante=False).count()
        
        return {
            'unread_notifications': unread_notifications,
            'pending_modal_notifications': pending_modal_notifications,
            'has_unread_notifs': unread_notifications.exists() or unread_tickets_count > 0,
            'unread_tickets_count': unread_tickets_count
        }
    return {}
