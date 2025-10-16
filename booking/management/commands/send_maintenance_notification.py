"""
Management command to send system maintenance completion notification to all users.
Usage: python manage.py send_maintenance_notification
"""
from django.core.management.base import BaseCommand
from booking.email_utils import send_system_maintenance_notification


class Command(BaseCommand):
    help = 'Send system maintenance completion notification to all active users'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING('Sending system maintenance notification to all active users...')
        )
        
        try:
            result = send_system_maintenance_notification()
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(
                        '✓ System maintenance notification sent successfully to all active users!'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        '✗ Failed to send system maintenance notification. Check logs for details.'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error: {str(e)}')
            )
