from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from booking.models import User
from django.template.loader import render_to_string

class Command(BaseCommand):
    help = 'Send system maintenance notification email to all active users.'

    def handle(self, *args, **options):
        subject = 'Scheduled System Maintenance Notification'
        users = User.objects.filter(is_active=True, email__isnull=False).exclude(email='')
        count = 0
        for user in users:
            html_message = render_to_string('emails/system_maintenance_notice.html', {'user': user})
            send_mail(
                subject,
                '',  # Plain text fallback
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Sent system maintenance emails to {count} users.'))
