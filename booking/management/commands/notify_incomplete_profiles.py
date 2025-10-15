from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from booking.models import User
from django.template.loader import render_to_string

class Command(BaseCommand):
    help = 'Send emails to users with incomplete profiles asking them to update their profile.'

    def handle(self, *args, **options):
        incomplete_users = User.objects.filter(
            models.Q(first_name__isnull=True) | models.Q(first_name='') |
            models.Q(last_name__isnull=True) | models.Q(last_name='') |
            models.Q(email__isnull=True) | models.Q(email='') |
            models.Q(school__isnull=True) | models.Q(school='') |
            models.Q(is_student=True, course__isnull=True) | models.Q(is_student=True, course='')
        ).distinct()

        count = 0
        for user in incomplete_users:
            if not user.email:
                continue
            subject = 'Please Update Your Profile - Lab Management System'
            message = render_to_string('emails/update_profile_reminder.html', {
                'user': user,
            })
            send_mail(
                subject,
                '',  # Plain text fallback
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=message,
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Sent profile update emails to {count} users.'))
