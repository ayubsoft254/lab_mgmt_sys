from django.core.management.base import BaseCommand
from booking.models import User

class Command(BaseCommand):
    help = 'Delete users with unverified emails.'

    def handle(self, *args, **options):
        # Assuming unverified users have is_active=False or email_verified=False
        # If you use django-allauth, you may have an EmailAddress model
        deleted_count = 0
        # Try to import EmailAddress if available
        try:
            from allauth.account.models import EmailAddress
            unverified_users = User.objects.filter(email__in=EmailAddress.objects.filter(verified=False).values_list('email', flat=True))
        except ImportError:
            # Fallback: delete users with is_active=False
            unverified_users = User.objects.filter(is_active=False)
        for user in unverified_users:
            user.delete()
            deleted_count += 1
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_count} unverified users.'))
