def notification_context(request):
    if request.user.is_authenticated:
        from .models import Notification
        return {
            'unread_notification_count': Notification.objects.filter(
                user=request.user, is_read=False
            ).count(),
        }
    return {'unread_notification_count': 0}
