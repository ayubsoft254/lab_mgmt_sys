"""
Email utilities for booking and session notifications.
Handles sending automated emails for booking/session approvals and rejections.
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def send_booking_approval_email(booking):
    """
    Send email to student when their booking is approved.
    Prevents duplicate emails by checking the approval_email_sent flag.
    
    Args:
        booking: ComputerBooking instance
    """
    # Prevent duplicate emails
    if booking.approval_email_sent:
        logger.info(f"Approval email already sent for booking {booking.id}, skipping")
        return True
    
    try:
        subject = f"Your Computer Booking Has Been Approved - {booking.computer}"
        
        # Prepare context for the email template
        context = {
            'student_name': booking.student.get_full_name(),
            'computer': booking.computer,
            'lab': booking.computer.lab.name,
            'start_time': booking.start_time.strftime('%B %d, %Y at %I:%M %p'),
            'end_time': booking.end_time.strftime('%I:%M %p'),
            'booking_code': booking.booking_code,
            'purpose': booking.purpose or 'Not specified',
            'booking_url': f"{settings.BASE_URL}/bookings/{booking.id}/" if settings.BASE_URL else "#",
        }
        
        # Render HTML and text versions
        html_message = render_to_string('emails/booking_approved.html', context)
        text_message = render_to_string('emails/booking_approved.txt', context)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[booking.student.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        # Mark email as sent
        booking.approval_email_sent = True
        booking.save(update_fields=['approval_email_sent'])
        
        logger.info(f"Booking approval email sent to {booking.student.email} for booking {booking.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking approval email: {str(e)}")
        return False


def send_booking_rejection_email(booking, rejection_reason=""):
    """
    Send email to student when their booking is rejected.
    Prevents duplicate emails by checking the rejection_email_sent flag.
    
    Args:
        booking: ComputerBooking instance
        rejection_reason: Optional reason for rejection
    """
    # Prevent duplicate emails
    if booking.rejection_email_sent:
        logger.info(f"Rejection email already sent for booking {booking.id}, skipping")
        return True
    
    try:
        subject = f"Your Computer Booking Has Been Rejected - {booking.computer}"
        
        context = {
            'student_name': booking.student.get_full_name(),
            'computer': booking.computer,
            'lab': booking.computer.lab.name,
            'start_time': booking.start_time.strftime('%B %d, %Y at %I:%M %p'),
            'end_time': booking.end_time.strftime('%I:%M %p'),
            'rejection_reason': rejection_reason or 'Booking request could not be accommodated.',
            'support_url': f"{settings.BASE_URL}/support/" if settings.BASE_URL else "#",
        }
        
        html_message = render_to_string('emails/booking_rejected.html', context)
        text_message = render_to_string('emails/booking_rejected.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[booking.student.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        # Mark email as sent
        booking.rejection_email_sent = True
        booking.save(update_fields=['rejection_email_sent'])
        
        logger.info(f"Booking rejection email sent to {booking.student.email} for booking {booking.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking rejection email: {str(e)}")
        return False


def send_session_approval_email(session):
    """
    Send email to lecturer when their lab session is approved.
    Prevents duplicate emails by checking the approval_email_sent flag.
    
    Args:
        session: LabSession instance
    """
    # Prevent duplicate emails
    if session.approval_email_sent:
        logger.info(f"Approval email already sent for session {session.id}, skipping")
        return True
    
    try:
        subject = f"Your Lab Session Has Been Approved - {session.title}"
        
        context = {
            'lecturer_name': session.lecturer.get_full_name(),
            'session_title': session.title,
            'lab': session.lab.name,
            'start_time': session.start_time.strftime('%B %d, %Y at %I:%M %p'),
            'end_time': session.end_time.strftime('%I:%M %p'),
            'student_count': session.attending_students.count(),
            'session_url': f"{settings.BASE_URL}/sessions/{session.id}/" if settings.BASE_URL else "#",
        }
        
        html_message = render_to_string('emails/session_approved.html', context)
        text_message = render_to_string('emails/session_approved.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[session.lecturer.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        # Mark email as sent
        session.approval_email_sent = True
        session.save(update_fields=['approval_email_sent'])
        
        logger.info(f"Session approval email sent to {session.lecturer.email} for session {session.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send session approval email: {str(e)}")
        return False


def send_session_rejection_email(session, rejection_reason=""):
    """
    Send email to lecturer when their lab session is rejected.
    Prevents duplicate emails by checking the rejection_email_sent flag.
    
    Args:
        session: LabSession instance
        rejection_reason: Optional reason for rejection
    """
    # Prevent duplicate emails
    if session.rejection_email_sent:
        logger.info(f"Rejection email already sent for session {session.id}, skipping")
        return True
    
    try:
        subject = f"Your Lab Session Has Been Rejected - {session.title}"
        
        context = {
            'lecturer_name': session.lecturer.get_full_name(),
            'session_title': session.title,
            'lab': session.lab.name,
            'start_time': session.start_time.strftime('%B %d, %Y at %I:%M %p'),
            'end_time': session.end_time.strftime('%I:%M %p'),
            'rejection_reason': rejection_reason or 'Session request could not be accommodated.',
            'support_url': f"{settings.BASE_URL}/support/" if settings.BASE_URL else "#",
        }
        
        html_message = render_to_string('emails/session_rejected.html', context)
        text_message = render_to_string('emails/session_rejected.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[session.lecturer.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        # Mark email as sent
        session.rejection_email_sent = True
        session.save(update_fields=['rejection_email_sent'])
        
        logger.info(f"Session rejection email sent to {session.lecturer.email} for session {session.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send session rejection email: {str(e)}")
        return False


def send_booking_cancellation_email(booking, cancelled_by=None, reason=""):
    """
    Send email to student when their booking is cancelled.
    Prevents duplicate emails by checking the cancellation_email_sent flag.
    
    Args:
        booking: ComputerBooking instance
        cancelled_by: String indicating who cancelled (admin or user)
        reason: Optional cancellation reason
    """
    # Prevent duplicate emails
    if booking.cancellation_email_sent:
        logger.info(f"Cancellation email already sent for booking {booking.id}, skipping")
        return True
    
    try:
        subject = f"Your Computer Booking Has Been Cancelled - {booking.computer}"
        
        context = {
            'student_name': booking.student.get_full_name(),
            'computer': booking.computer,
            'lab': booking.computer.lab.name,
            'start_time': booking.start_time.strftime('%B %d, %Y at %I:%M %p'),
            'end_time': booking.end_time.strftime('%I:%M %p'),
            'cancelled_by': cancelled_by or 'Administrator',
            'cancellation_reason': reason or 'No reason provided.',
            'support_url': f"{settings.BASE_URL}/support/" if settings.BASE_URL else "#",
        }
        
        html_message = render_to_string('emails/booking_cancelled.html', context)
        text_message = render_to_string('emails/booking_cancelled.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[booking.student.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        # Mark email as sent
        booking.cancellation_email_sent = True
        booking.save(update_fields=['cancellation_email_sent'])
        
        logger.info(f"Booking cancellation email sent to {booking.student.email} for booking {booking.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking cancellation email: {str(e)}")
        return False


def send_session_cancellation_email(session, cancelled_by=None, reason=""):
    """
    Send email to lecturer when their session is cancelled.
    Prevents duplicate emails by checking the cancellation_email_sent flag.
    
    Args:
        session: LabSession instance
        cancelled_by: String indicating who cancelled
        reason: Optional cancellation reason
    """
    # Prevent duplicate emails
    if session.cancellation_email_sent:
        logger.info(f"Cancellation email already sent for session {session.id}, skipping")
        return True
    
    try:
        subject = f"Your Lab Session Has Been Cancelled - {session.title}"
        
        context = {
            'lecturer_name': session.lecturer.get_full_name(),
            'session_title': session.title,
            'lab': session.lab.name,
            'start_time': session.start_time.strftime('%B %d, %Y at %I:%M %p'),
            'end_time': session.end_time.strftime('%I:%M %p'),
            'cancelled_by': cancelled_by or 'Administrator',
            'cancellation_reason': reason or 'No reason provided.',
            'support_url': f"{settings.BASE_URL}/support/" if settings.BASE_URL else "#",
        }
        
        html_message = render_to_string('emails/session_cancelled.html', context)
        text_message = render_to_string('emails/session_cancelled.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[session.lecturer.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        # Mark email as sent
        session.cancellation_email_sent = True
        session.save(update_fields=['cancellation_email_sent'])
        
        logger.info(f"Session cancellation email sent to {session.lecturer.email} for session {session.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send session cancellation email: {str(e)}")
        return False


def send_system_maintenance_notification():
    """
    Send system maintenance completion notification to all active users.
    Notifies students and lecturers that the system is now fully operational.
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get all active users (students and lecturers)
        active_users = User.objects.filter(
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        if not active_users.exists():
            logger.warning("No active users found to send maintenance notification")
            return False
        
        subject = "System Maintenance Complete - Lab Management System Now Fully Active"
        
        context = {
            'support_email': 'ictlabs@ttu.ac.ke',
            'support_phone': '+254113364472',
            'system_name': 'Lab Management System',
        }
        
        html_message = render_to_string('emails/system_maintenance_notification.html', context)
        text_message = render_to_string('emails/system_maintenance_notification.txt', context)
        
        # Send email to all active users
        for user in active_users:
            try:
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,
                    from_email=settings.EMAIL_HOST_USER,
                    to=[user.email]
                )
                email.attach_alternative(html_message, "text/html")
                email.send(fail_silently=False)
                logger.info(f"System maintenance notification sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send maintenance notification to {user.email}: {str(e)}")
                continue
        
        logger.info(f"System maintenance notification sent to {active_users.count()} users")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send system maintenance notification: {str(e)}")
        return False
