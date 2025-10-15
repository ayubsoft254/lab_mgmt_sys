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
    
    Args:
        booking: ComputerBooking instance
    """
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
        
        logger.info(f"Booking approval email sent to {booking.student.email} for booking {booking.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking approval email: {str(e)}")
        return False


def send_booking_rejection_email(booking, rejection_reason=""):
    """
    Send email to student when their booking is rejected.
    
    Args:
        booking: ComputerBooking instance
        rejection_reason: Optional reason for rejection
    """
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
        
        logger.info(f"Booking rejection email sent to {booking.student.email} for booking {booking.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking rejection email: {str(e)}")
        return False


def send_session_approval_email(session):
    """
    Send email to lecturer when their lab session is approved.
    
    Args:
        session: LabSession instance
    """
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
        
        logger.info(f"Session approval email sent to {session.lecturer.email} for session {session.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send session approval email: {str(e)}")
        return False


def send_session_rejection_email(session, rejection_reason=""):
    """
    Send email to lecturer when their lab session is rejected.
    
    Args:
        session: LabSession instance
        rejection_reason: Optional reason for rejection
    """
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
        
        logger.info(f"Session rejection email sent to {session.lecturer.email} for session {session.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send session rejection email: {str(e)}")
        return False


def send_booking_cancellation_email(booking, cancelled_by=None, reason=""):
    """
    Send email to student when their booking is cancelled.
    
    Args:
        booking: ComputerBooking instance
        cancelled_by: String indicating who cancelled (admin or user)
        reason: Optional cancellation reason
    """
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
        
        logger.info(f"Booking cancellation email sent to {booking.student.email} for booking {booking.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking cancellation email: {str(e)}")
        return False


def send_session_cancellation_email(session, cancelled_by=None, reason=""):
    """
    Send email to lecturer when their session is cancelled.
    
    Args:
        session: LabSession instance
        cancelled_by: String indicating who cancelled
        reason: Optional cancellation reason
    """
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
        
        logger.info(f"Session cancellation email sent to {session.lecturer.email} for session {session.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send session cancellation email: {str(e)}")
        return False
