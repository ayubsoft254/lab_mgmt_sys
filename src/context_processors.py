"""
Custom context processors for the Lab Management System.
"""
from django.utils import timezone
from datetime import datetime
from booking.models import Notification


def notifications_context(request):
    """
    Add unread notifications count to the template context.
    """
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        )
        unread_notifications_count = unread_notifications.count()
    else:
        unread_notifications_count = 0
    
    return {
        'unread_notifications_count': unread_notifications_count
    }


def datetime_serializable_context(request):
    """
    Add utilities for making datetime objects JSON serializable.
    This helps prevent JSON serialization errors in templates.
    """
    return {
        'now': timezone.now(),
    }
