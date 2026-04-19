from .models import Notification

def notification_context(request):
    if request.user.is_authenticated:
        # Notificações para o sininho (não lidas)
        unread_notifications = Notification.objects.filter(user=request.user, lida=False)
        
        # Notificações para o modal central (não exibidas)
        pending_modal_notifications = Notification.objects.filter(user=request.user, exibida_em_modal=False)
        
        return {
            'unread_notifications': unread_notifications,
            'pending_modal_notifications': pending_modal_notifications,
            'has_unread_notifs': unread_notifications.exists()
        }
    return {}
