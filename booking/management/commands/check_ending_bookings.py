from django.core.management.base import BaseCommand
from django.utils import timezone
from booking.models import ComputerBooking, Notification
from datetime import timedelta

class Command(BaseCommand):
    help = 'Check for bookings that are ending soon and send notifications'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Find bookings ending in the next 5-6 minutes that haven't had reminders sent
        ending_soon = ComputerBooking.objects.filter(
            end_time__gt=now + timedelta(minutes=5),
            end_time__lte=now + timedelta(minutes=6),
            is_approved=True,
            is_cancelled=False,
            reminder_sent=False
        )
        
        for booking in ending_soon:
            # Create notification for user
            message = (
                f"Your booking for {booking.computer} ends in 5 minutes. "
            )
            
            # Check if extension is possible
            if booking.can_be_extended():
                message += "You can extend your session by 30 minutes."
                notification_type = 'booking_ending'
            else:
                message += "No extension is available at this time."
                notification_type = 'extension_unavailable'
            
            Notification.objects.create(
                user=booking.student,
                message=message,
                notification_type=notification_type,
                booking=booking
            )
            
            # Mark reminder as sent
            booking.reminder_sent = True
            booking.save(update_fields=['reminder_sent'])
            
            self.stdout.write(
                self.style.SUCCESS(f'Sent reminder for booking {booking.id}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Processed {ending_soon.count()} ending bookings')
        )