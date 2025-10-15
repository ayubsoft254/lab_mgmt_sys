from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import ComputerBooking, LabSession, Notification, User
from datetime import timedelta

@shared_task
def check_ending_bookings():
    """Check for bookings that are ending soon and send notifications"""
    now = timezone.now()
    
    # Find bookings ending in the next 5-6 minutes that haven't had reminders sent
    ending_soon = ComputerBooking.objects.filter(
        end_time__gt=now + timedelta(minutes=5),
        end_time__lte=now + timedelta(minutes=6),
        is_approved=True,
        is_cancelled=False,
        reminder_sent=False
    )
    
    count = 0
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
        count += 1
    
    return f'Processed {count} ending bookings'


@shared_task
def notify_admins_pending_bookings():
    """Send email notifications to admins about pending bookings that need approval"""
    try:
        # Get all pending (unapproved) bookings
        pending_bookings = ComputerBooking.objects.filter(
            is_approved=False,
            is_cancelled=False
        ).select_related('computer', 'computer__lab', 'student').order_by('created_at')
        
        if not pending_bookings.exists():
            return 'No pending bookings to notify'
        
        # Get all admin users
        admins = User.objects.filter(is_admin=True) | User.objects.filter(is_super_admin=True)
        admins = admins.distinct()
        
        if not admins.exists():
            return 'No admins found'
        
        # Group bookings by lab for relevant admins
        bookings_by_lab = {}
        for booking in pending_bookings:
            lab = booking.computer.lab
            if lab not in bookings_by_lab:
                bookings_by_lab[lab] = []
            bookings_by_lab[lab].append(booking)
        
        # Send emails to relevant admins
        email_count = 0
        for admin in admins:
            # Determine which bookings are relevant to this admin
            relevant_bookings = []
            
            if admin.is_super_admin:
                # Super admins get all pending bookings
                relevant_bookings = list(pending_bookings)
            else:
                # Lab admins get bookings from their managed labs
                relevant_labs = admin.managed_labs.all()
                for lab in relevant_labs:
                    if lab in bookings_by_lab:
                        relevant_bookings.extend(bookings_by_lab[lab])
            
            if relevant_bookings:
                # Send email to this admin
                _send_admin_pending_bookings_email(admin, relevant_bookings)
                email_count += 1
        
        return f'Sent pending bookings notifications to {email_count} admins'
    
    except Exception as e:
        print(f"Error in notify_admins_pending_bookings: {e}")
        return f'Error: {str(e)}'


@shared_task
def notify_admins_pending_sessions():
    """Send email notifications to admins about pending sessions that need approval"""
    try:
        # Get all pending (unapproved) sessions
        pending_sessions = LabSession.objects.filter(
            is_approved=False,
            is_cancelled=False
        ).select_related('lab', 'lecturer').order_by('created_at')
        
        if not pending_sessions.exists():
            return 'No pending sessions to notify'
        
        # Get all admin users
        admins = User.objects.filter(is_admin=True) | User.objects.filter(is_super_admin=True)
        admins = admins.distinct()
        
        if not admins.exists():
            return 'No admins found'
        
        # Group sessions by lab for relevant admins
        sessions_by_lab = {}
        for session in pending_sessions:
            lab = session.lab
            if lab not in sessions_by_lab:
                sessions_by_lab[lab] = []
            sessions_by_lab[lab].append(session)
        
        # Send emails to relevant admins
        email_count = 0
        for admin in admins:
            # Determine which sessions are relevant to this admin
            relevant_sessions = []
            
            if admin.is_super_admin:
                # Super admins get all pending sessions
                relevant_sessions = list(pending_sessions)
            else:
                # Lab admins get sessions from their managed labs
                relevant_labs = admin.managed_labs.all()
                for lab in relevant_labs:
                    if lab in sessions_by_lab:
                        relevant_sessions.extend(sessions_by_lab[lab])
            
            if relevant_sessions:
                # Send email to this admin
                _send_admin_pending_sessions_email(admin, relevant_sessions)
                email_count += 1
        
        return f'Sent pending sessions notifications to {email_count} admins'
    
    except Exception as e:
        print(f"Error in notify_admins_pending_sessions: {e}")
        return f'Error: {str(e)}'


# Helper functions for sending emails

def _send_admin_pending_bookings_email(admin, bookings):
    """Send email to admin about pending bookings"""
    try:
        subject = f'Pending Computer Bookings Requiring Approval ({len(bookings)} pending)'
        
        context = {
            'admin': admin,
            'bookings': bookings,
            'pending_count': len(bookings),
            'admin_dashboard_url': f"{settings.BASE_URL}/Dashboard/",
            'base_url': settings.BASE_URL,
        }
        
        html_message = render_to_string('emails/admin_pending_bookings_notification.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending admin pending bookings email: {e}")


def _send_admin_pending_sessions_email(admin, sessions):
    """Send email to admin about pending sessions"""
    try:
        subject = f'Pending Lab Sessions Requiring Approval ({len(sessions)} pending)'
        
        context = {
            'admin': admin,
            'sessions': sessions,
            'pending_count': len(sessions),
            'admin_dashboard_url': f"{settings.BASE_URL}/Dashboard/",
            'base_url': settings.BASE_URL,
        }
        
        html_message = render_to_string('emails/admin_pending_sessions_notification.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending admin pending sessions email: {e}")