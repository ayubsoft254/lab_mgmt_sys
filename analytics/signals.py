from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import SystemEvent

@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    ip_address = request.META.get('REMOTE_ADDR', '')
    SystemEvent.objects.create(
        user=user,
        event_type='login',
        ip_address=ip_address,
        details={'user_agent': request.META.get('HTTP_USER_AGENT', '')}
    )

@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    if user:  # user can be None if the session was already deleted
        ip_address = request.META.get('REMOTE_ADDR', '')
        SystemEvent.objects.create(
            user=user,
            event_type='logout',
            ip_address=ip_address
        )