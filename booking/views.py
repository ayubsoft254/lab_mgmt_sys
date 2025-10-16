from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse as DjangoJsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from datetime import datetime, timedelta
from src.json_encoders import JsonResponse

from .models import (
    User, Lab, Computer, ComputerBooking, LabSession, 
    Notification, RecurringSession, StudentRating, ComputerBookingAttendance, 
    SessionAttendance
)
from .forms import (
    ComputerBookingForm, LabSessionForm, RecurringSessionForm, 
    StudentRatingForm, UserProfileForm, AttendanceForm, BulkAttendanceForm
)
from .email_utils import (
    send_booking_approval_email, send_booking_rejection_email,
    send_session_approval_email, send_session_rejection_email,
    send_booking_cancellation_email, send_session_cancellation_email
)
 
class LandingPageView(TemplateView):
    template_name = 'landing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get statistics for the landing page safely
            context['active_students'] = int(User.objects.filter(is_student=True).count())
            context['lab_count'] = int(Lab.objects.count())

            
            # Calculate system uptime percentage more safely
            total_bookings = ComputerBooking.objects.count()
            if total_bookings > 0:
                successful_bookings = ComputerBooking.objects.filter(is_approved=True).count()
                # Never divide by zero, and ensure it's a float division
                uptime_percentage = round((successful_bookings / float(total_bookings)) * 100, 1)
            else:
                uptime_percentage = 100  # Default if no bookings yet
            
            # Ensure the percentage is reasonable
            uptime_percentage = min(max(uptime_percentage, 95), 99.9)  # Between 95% and 99.9%
            context['uptime_percentage'] = uptime_percentage
            
            # Get total hours of lab usage in the past month more safely
            one_month_ago = timezone.now() - timedelta(days=30)
            
            # Sum duration of all bookings in the past month using database aggregation
            from django.db.models import F, ExpressionWrapper, Sum, DurationField
            
            # Calculate duration as a database expression
            recent_bookings = ComputerBooking.objects.filter(
                start_time__gte=one_month_ago,
                is_approved=True
            ).annotate(
                duration=ExpressionWrapper(
                    F('end_time') - F('start_time'), 
                    output_field=DurationField()
                )
            )
            
            # Sum all durations
            total_duration = recent_bookings.aggregate(
                total=Sum('duration')
            )['total'] or timedelta(0)  # Default to 0 if None
            
            # Convert to hours
            total_hours = total_duration.total_seconds() / 3600
            context['total_hours'] = int(total_hours)
            
        except Exception as e:
            # Log the error and provide fallback values
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in landing page stats calculation: {str(e)}")
            
            # Provide fallback values
            context['active_students'] = 50
            context['lab_count'] = 4
            context['uptime_percentage'] = 99.0
            context['total_hours'] = 1899
        
        return context
    
class SupportPageView(TemplateView):
    template_name = 'support.html'   
    
@login_required
def home_view(request):
    upcoming_bookings = None
    upcoming_sessions = None
    recurring_sessions = None
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    
    if request.user.is_student:
        upcoming_bookings = ComputerBooking.objects.filter(
            student=request.user,
            end_time__gte=timezone.now(),
            is_cancelled=False
        ).order_by('start_time')
    
    if request.user.is_lecturer:
        upcoming_sessions = LabSession.objects.filter(
            lecturer=request.user,
            end_time__gte=timezone.now()
        ).order_by('start_time')
        
        recurring_sessions = RecurringSession.objects.filter(
            lecturer=request.user,
            is_approved=True,
            end_date__gte=timezone.now().date()
        ).order_by('start_date')
    
    labs = Lab.objects.all()
    
    return render(request, 'home.html', {
        'labs': labs,
        'upcoming_bookings': upcoming_bookings,
        'upcoming_sessions': upcoming_sessions,
        'recurring_sessions': recurring_sessions,
        'notifications': notifications
    })

@login_required
def lab_list_view(request):
    labs = Lab.objects.all()
    return render(request, 'lab_list.html', {'labs': labs})

@login_required
def lab_detail_view(request, lab_id):
    lab = get_object_or_404(Lab, id=lab_id)
    computers = Computer.objects.filter(lab=lab)
    
    # Get all upcoming sessions for this lab
    upcoming_sessions = LabSession.objects.filter(
        lab=lab,
        end_time__gte=timezone.now(),
        is_approved=True
    ).order_by('start_time')
    
    return render(request, 'lab_detail.html', {
        'lab': lab,
        'computers': computers,
        'upcoming_sessions': upcoming_sessions
    })

@login_required
def student_booking_view(request, lab_id, computer_id=None):
    if not request.user.is_student:
        messages.error(request, "Only students can book computers")
        return redirect('lab_detail', lab_id=lab_id)
    
    lab = get_object_or_404(Lab, id=lab_id)
    computer = None
    if computer_id:
        computer = get_object_or_404(Computer, id=computer_id, lab=lab)
    
    if request.method == 'POST':
        form = ComputerBookingForm(request.POST, lab_id=lab_id)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.student = request.user
            booking.save()
            
            # Updated notification with proper reference to booking
            admin_users = User.objects.filter(is_admin=True)
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    message=f"New computer booking: {booking.computer} by {request.user.username}",
                    notification_type='new_booking',
                    booking=booking  # Add direct reference to booking
                )
            
            return redirect('booking_success', booking_id=booking.id)
    else:
        initial_data = {}
        if computer:
            initial_data['computer'] = computer.id
        
        form = ComputerBookingForm(lab_id=lab_id, initial=initial_data)
    
    return render(request, 'student_booking.html', {
        'form': form,
        'lab': lab,
        'computer': computer
    })

@login_required
def lecturer_booking_view(request):
    if not request.user.is_lecturer:
        messages.error(request, "Only lecturers can book lab sessions")
        return redirect('home')
    
    if request.method == 'POST':
        form = LabSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.lecturer = request.user
            
            try:
                session.save()
                
                # Updated notification with proper reference to lab session
                admin_users = User.objects.filter(is_admin=True)
                for admin in admin_users:
                    Notification.objects.create(
                        user=admin,
                        message=f"New lab session request: {session.lab.name} by {request.user.username}",
                        notification_type='session_booked',
                        lab_session=session  # Add direct reference to session
                    )
                
                messages.success(request, "Lab session request submitted for approval")
                return redirect('home')
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, error)
    else:
        form = LabSessionForm()
    
    return render(request, 'lecturer_booking.html', {'form': form})

@login_required
def booking_success_view(request, booking_id):
    booking = get_object_or_404(ComputerBooking, id=booking_id, student=request.user)
    return render(request, 'booking_success.html', {'booking': booking})

@login_required
def admin_dashboard_view(request):
    if not request.user.is_admin and not request.user.is_super_admin:
        messages.error(request, "You do not have permission to access the admin dashboard.")
        return redirect('home')
    
    # For super admins, show all bookings
    if request.user.is_super_admin:
        pending_computer_bookings = ComputerBooking.objects.filter(
            is_approved=False, 
            is_cancelled=False
        ).order_by('start_time')
        
        pending_lab_sessions = LabSession.objects.filter(
            is_approved=False
        ).order_by('start_time')
        
        pending_recurring_sessions = RecurringSession.objects.filter(
            is_approved=False
        ).order_by('start_date')
    else:
        # For lab-specific admins, only show bookings for their managed labs
        managed_labs = request.user.managed_labs.all()
        
        pending_computer_bookings = ComputerBooking.objects.filter(
            computer__lab__in=managed_labs,
            is_approved=False, 
            is_cancelled=False
        ).order_by('start_time')
        
        pending_lab_sessions = LabSession.objects.filter(
            lab__in=managed_labs,
            is_approved=False
        ).order_by('start_time')
        
        pending_recurring_sessions = RecurringSession.objects.filter(
            lab__in=managed_labs,
            is_approved=False
        ).order_by('start_date')
    
    # Continue with rest of the view logic...
    
    now = timezone.now()
    
    # Pending approvals
    pending_computer_bookings = ComputerBooking.objects.filter(
        is_approved=False,
        is_cancelled=False,
        end_time__gte=now
    ).order_by('start_time')
    
    pending_lab_sessions = LabSession.objects.filter(
        is_approved=False,
        end_time__gte=now
    ).order_by('start_time')

    pending_recurring_sessions = RecurringSession.objects.filter(
        is_approved=False,        
        end_time__gte=now
    ).order_by('start_date')
    
    # Upcoming (approved) bookings and sessions
    upcoming_computer_bookings = ComputerBooking.objects.filter(
        is_approved=True,
        is_cancelled=False,
        end_time__gte=now  # Show bookings from now onwards
    ).order_by('start_time')
    
    upcoming_lab_sessions = LabSession.objects.filter(
        is_approved=True,
        end_time__gte=now  # Show sessions from now onwards
    ).order_by('start_time')
    
    # Past bookings and sessions
    past_computer_bookings = ComputerBooking.objects.filter(
        end_time__lt=now
    ).order_by('-start_time')[:20]  # Limit to recent 20 for performance
    
    past_lab_sessions = LabSession.objects.filter(
        end_time__lt=now
    ).order_by('-start_time')[:20]  # Limit to recent 20 for performance
    
    # Filter by date range if provided
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from and date_to:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            date_to = timezone.datetime.combine(date_to, timezone.datetime.max.time())  # End of day
            
            # Apply filters to past records
            past_computer_bookings = ComputerBooking.objects.filter(
                end_time__lt=now,
                start_time__gte=date_from,
                end_time__lte=date_to
            ).order_by('-start_time')
            
            past_lab_sessions = LabSession.objects.filter(
                end_time__lt=now,
                start_time__gte=date_from,
                end_time__lte=date_to
            ).order_by('-start_time')
            
            # Apply filters to upcoming records
            upcoming_computer_bookings = ComputerBooking.objects.filter(
                is_approved=True,
                is_cancelled=False,
                start_time__gte=date_from,
                end_time__lte=date_to
            ).order_by('start_time')
            
            upcoming_lab_sessions = LabSession.objects.filter(
                is_approved=True,
                start_time__gte=date_from,
                end_time__lte=date_to
            ).order_by('start_time')
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
    
    # Get basic stats
    stats = {
        'total_labs': Lab.objects.count(),
        'total_computers': Computer.objects.count(),
        'available_computers': Computer.objects.filter(status='available').count(),
        'maintenance_computers': Computer.objects.filter(status='maintenance').count(),
        'pending_bookings_count': pending_computer_bookings.count(),
        'pending_sessions_count': pending_lab_sessions.count(),
        'pending_recurring_sessions': RecurringSession.objects.filter(is_approved=False,).count(),
        'total_pending_approvals': pending_computer_bookings.count() + pending_lab_sessions.count(),
    }
    
    labs = Lab.objects.all()    
    
    # Get approved recurring sessions for the Recurring Sessions tab
    approved_recurring_sessions = RecurringSession.objects.filter(
        is_approved=True
    ).order_by('start_date')
    
    # Add this:
    today = timezone.now().date()
    today_bookings = ComputerBooking.objects.filter(
        start_time__date=today
    )
    today_sessions = LabSession.objects.filter(
        start_time__date=today
    )

    students = User.objects.filter(is_student=True).order_by('username')

    context = {
        'pending_computer_bookings': pending_computer_bookings,        
        'pending_lab_sessions': pending_lab_sessions,              
        'upcoming_computer_bookings': upcoming_computer_bookings,
        'upcoming_lab_sessions': upcoming_lab_sessions,
        'past_computer_bookings': past_computer_bookings,
        'past_lab_sessions': past_lab_sessions,
        'stats': stats,
        'labs': labs,
        'date_from': date_from,
        'date_to': date_to,
        'pending_recurring_sessions': pending_recurring_sessions,
        'approved_recurring_sessions': approved_recurring_sessions,
        'students': students,
    }
    
    
    # Add these to the context in admin_check_in_dashboard view
    context.update({
        'debug_info': {
            'today': today.isoformat() if today else None,
            'timezone_now': timezone.now().isoformat(),
            'today_bookings_count': today_bookings.count(),
            'today_sessions_count': today_sessions.count(),
            'today_bookings_times': [
                (b.id, b.start_time.isoformat(), b.end_time.isoformat()) for b in today_bookings[:5]
            ],
            'today_sessions_times': [
                (s.id, s.start_time.isoformat(), s.end_time.isoformat()) for s in today_sessions[:5]
            ]
        }
    })
    
    # Add this to the admin_check_in_dashboard view:
    session_attendance = {}
    for session in today_sessions:
        # Get count of students marked as present for this session
        present_count = SessionAttendance.objects.filter(
            session=session,
            status='present'
        ).count()
        session_attendance[session.id] = present_count

    context['session_attendance'] = session_attendance
    
    # In admin_check_in_dashboard view
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today
    
    # Use selected_date instead of today in your queries
    context['today'] = selected_date
    context['tomorrow'] = selected_date + timedelta(days=1)
    
    return render(request, 'admin_dashboard.html', context)

@login_required
def approve_booking_view(request, booking_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    booking = get_object_or_404(ComputerBooking, id=booking_id)
    
    try:
        booking.is_approved = True
        booking.save()
        
        # Updated notification with proper reference
        Notification.objects.create(
            user=booking.student,
            message=f"Your booking for {booking.computer} has been approved.",
            notification_type='booking_approved',
            booking=booking  # Add direct reference
        )
        
        # Send approval email to student
        send_booking_approval_email(booking)
        
        messages.success(request, "Booking approved successfully and confirmation email sent")
    except ValidationError as e:
        booking.is_approved = False
        messages.error(request, f"Cannot approve booking: {', '.join(e.messages)}")
    
    return redirect('admin_dashboard')

@login_required
def approve_session_view(request, session_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    session = get_object_or_404(LabSession, id=session_id)
    
    try:
        session.is_approved = True
        session.save()
        
        # Updated notification with proper reference
        Notification.objects.create(
            user=session.lecturer,
            message=f"Your session for {session.lab.name} has been approved.",
            notification_type='booking_approved',
            lab_session=session  # Add direct reference
        )
        
        # Send approval email to lecturer
        send_session_approval_email(session)
        
        messages.success(request, "Lab session approved successfully and confirmation email sent")
    except ValidationError as e:
        session.is_approved = False
        messages.error(request, f"Cannot approve session: {', '.join(e.messages)}")
    
    return redirect('admin_dashboard')

@login_required
def notification_list_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect('notification_list')
    
    return render(request, 'notification_list.html', {
        'notifications': notifications
    })

@login_required
def free_timeslots_view(request, lab_id=None, computer_id=None):
    from datetime import time  # Add this import
    
    # Determine the scope of the search (lab-wide or computer-specific)
    if computer_id:
        computer = get_object_or_404(Computer, id=computer_id)
        lab = computer.lab
    elif lab_id:
        lab = get_object_or_404(Lab, id=lab_id)
        computer = None
    else:
        # If no specific lab or computer is selected, show labs list
        labs = Lab.objects.all()
        return render(request, 'free_timeslots_select.html', {
            'labs': labs
        })
    
    # Set up date range (next 7 days)
    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=7)
    
    # Get all booked time slots
    if computer:
        # Computer-specific bookings
        booked_slots = ComputerBooking.objects.filter(
            computer=computer,
            is_approved=True,
            is_cancelled=False,
            start_time__date__range=[start_date, end_date]
        )
    else:
        # Lab-wide sessions and bookings
        booked_lab_sessions = LabSession.objects.filter(
            lab=lab,
            is_approved=True,
            start_time__date__range=[start_date, end_date]
        )
        booked_computer_bookings = ComputerBooking.objects.filter(
            computer__lab=lab,
            is_approved=True,
            is_cancelled=False,
            start_time__date__range=[start_date, end_date]
        )
    
    # Prepare time slots
    time_slots = []
    current_date = start_date
    while current_date <= end_date:
        # Generate hourly slots from 8:00 AM to 8:00 PM
        for hour in range(8, 20):
            slot_start_time = time(hour=hour, minute=0)
            slot_start = timezone.make_aware(datetime.combine(current_date, slot_start_time))
            slot_end = slot_start + timedelta(hours=1)

            # Check if slot is free
            if computer:
                is_free = not booked_slots.filter(
                    start_time__lt=slot_end,
                    end_time__gt=slot_start
                ).exists()
            else:
                is_free = not (
                    booked_lab_sessions.filter(
                        start_time__lt=slot_end,
                        end_time__gt=slot_start
                    ).exists() or
                    booked_computer_bookings.filter(
                        start_time__lt=slot_end,
                        end_time__gt=slot_start
                    ).exists()
                )

            # Add is_weekend property
            is_weekend = current_date.weekday() >= 5  # 5=Saturday, 6=Sunday

            time_slots.append({
                'date': current_date,
                'start_time': slot_start,
                'end_time': slot_end,
                'is_free': is_free,
                'is_weekend': is_weekend
            })
        current_date += timedelta(days=1)
    
    return render(request, 'free_timeslots.html', {
        'lab': lab,
        'computer': computer,
        'time_slots': time_slots
    })

@login_required
def recurring_booking_view(request):
    if not request.user.is_lecturer:
        messages.error(request, "Only lecturers can book recurring sessions")
        return redirect('home')
    
    if request.method == 'POST':
        form = RecurringSessionForm(request.POST)
        if form.is_valid():
            recurring_session = form.save(commit=False)
            recurring_session.lecturer = request.user
            
            try:
                recurring_session.save()
                
                # Updated notification with proper type and reference
                admin_users = User.objects.filter(is_admin=True)
                for admin in admin_users:
                    Notification.objects.create(
                        user=admin,
                        message=f"New recurring session request: {recurring_session.lab.name} - {recurring_session.title}",
                        notification_type='recurring_session_created',  # Updated type
                        recurring_session=recurring_session  # Add direct reference
                    )
                
                messages.success(request, "Recurring session request submitted for approval")
                return redirect('home')
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, error)
    else:
        form = RecurringSessionForm()
    
    return render(request, 'recurring_booking.html', {'form': form})

@login_required
def recurring_sessions_list_view(request):
    if request.user.is_lecturer:
        # Show lecturer's recurring sessions
        recurring_sessions = RecurringSession.objects.filter(
            lecturer=request.user
        ).order_by('-created_at')
    elif request.user.is_admin:
        # Show all recurring sessions for admin
        recurring_sessions = RecurringSession.objects.all().order_by('-created_at')
    else:
        # Unauthorized access
        messages.error(request, "You are not authorized to view recurring sessions")
        return redirect('home')
    
    return render(request, 'recurring_sessions_list.html', {
        'recurring_sessions': recurring_sessions
    })

@login_required
def cancel_recurring_session_view(request, session_id):
    recurring_session = get_object_or_404(RecurringSession, id=session_id)
    
    # Ensure only the lecturer who created the session or an admin can cancel
    if not (request.user == recurring_session.lecturer or request.user.is_admin):
        messages.error(request, "You are not authorized to cancel this recurring session")
        return redirect('recurring_sessions_list')
    
    if request.method == 'POST':
        # Delete all future lab sessions associated with this recurring session
        LabSession.objects.filter(
            lab=recurring_session.lab,
            lecturer=recurring_session.lecturer,
            title=recurring_session.title,
            start_time__gte=timezone.now()
        ).delete()
        
        # Delete the recurring session
        recurring_session.delete()
        
        # Add notification for cancellation
        if request.user.is_admin:
            # Admin cancelled a session, notify the lecturer
            Notification.objects.create(
                user=recurring_session.lecturer,
                message=f"Your recurring session '{recurring_session.title}' has been cancelled by an administrator.",
                notification_type='recurring_session_rejected',
                recurring_session=recurring_session
            )
        elif request.user == recurring_session.lecturer:
            # Lecturer cancelled their own session, notify admins
            admin_users = User.objects.filter(is_admin=True)
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    message=f"Recurring session '{recurring_session.title}' was cancelled by {recurring_session.lecturer.username}.",
                    notification_type='recurring_session_rejected',
                    recurring_session=recurring_session
                )
        
        messages.success(request, "Recurring session cancelled successfully")
        return redirect('recurring_sessions_list')
    
    return render(request, 'cancel_recurring_session.html', {
        'recurring_session': recurring_session
    })

# NEW FUNCTION: Add approve recurring session view
@login_required
def approve_recurring_session_view(request, session_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    recurring_session = get_object_or_404(RecurringSession, id=session_id)
    recurring_session.is_approved = True
    recurring_session.save()
    
    # Create notification with direct reference
    Notification.objects.create(
        user=recurring_session.lecturer,
        message=f"Your recurring session '{recurring_session.title}' for {recurring_session.lab.name} has been approved.",
        notification_type='recurring_session_approved',
        recurring_session=recurring_session
    )
    
    messages.success(request, "Recurring session approved successfully")
    return redirect('admin_dashboard')

# NEW FUNCTION: Add reject recurring session view
@login_required
def reject_recurring_session_view(request, session_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    recurring_session = get_object_or_404(RecurringSession, id=session_id)
    
    # Create rejection notification before deleting
    Notification.objects.create(
        user=recurring_session.lecturer,
        message=f"Your recurring session request '{recurring_session.title}' for {recurring_session.lab.name} has been rejected.",
        notification_type='recurring_session_rejected',
        recurring_session=recurring_session
    )
    
    # Delete the recurring session
    recurring_session.delete()
    
    messages.success(request, "Recurring session rejected successfully")
    return redirect('admin_dashboard')

@login_required
def bulk_approve_bookings_view(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    if request.method == 'POST':
        # Approve all pending bookings
        pending_bookings = ComputerBooking.objects.filter(is_approved=False, is_cancelled=False, end_time__gte=timezone.now())
        
        count = 0
        for booking in pending_bookings:
            booking.is_approved = True
            booking.save()
            
            # Create notification
            Notification.objects.create(
                user=booking.student,
                message=f"Your booking for {booking.computer} has been approved.",
                notification_type='booking_approved',
                booking=booking
            )
            
            # Send approval email
            send_booking_approval_email(booking)
            count += 1
        
        messages.success(request, f"{count} bookings approved successfully and confirmation emails sent")
    
    return redirect('admin_dashboard')

@login_required
def bulk_approve_sessions_view(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    if request.method == 'POST':
        # Approve all pending lab sessions
        pending_sessions = LabSession.objects.filter(is_approved=False, end_time__gte=timezone.now())
        
        count = 0
        for session in pending_sessions:
            session.is_approved = True
            session.save()
            
            # Create notification
            Notification.objects.create(
                user=session.lecturer,
                message=f"Your session for {session.lab.name} has been approved.",
                notification_type='booking_approved',
                lab_session=session
            )
            
            # Send approval email
            send_session_approval_email(session)
            count += 1
        
        messages.success(request, f"{count} lab sessions approved successfully and confirmation emails sent")
    
    return redirect('admin_dashboard')

@login_required
def bulk_approve_recurring_sessions_view(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    if request.method == 'POST':
        # Approve all pending recurring sessions
        pending_recurring_sessions = RecurringSession.objects.filter(is_approved=False)
        
        count = 0
        for session in pending_recurring_sessions:
            session.is_approved = True
            session.save()
            
            # Create notification
            Notification.objects.create(
                user=session.lecturer,
                message=f"Your recurring session '{session.title}' for {session.lab.name} has been approved.",
                notification_type='recurring_session_approved',
                recurring_session=session
            )
            count += 1
        
        messages.success(request, f"{count} recurring sessions approved successfully")
    
    return redirect('admin_dashboard')

@login_required
def bulk_cancel_bookings_view(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    if request.method == 'POST':
        # Cancel all upcoming bookings
        upcoming_bookings = ComputerBooking.objects.filter(
            is_approved=True,
            is_cancelled=False,
            end_time__gte=timezone.now()
        )
        
        count = 0
        for booking in upcoming_bookings:
            booking.is_cancelled = True
            booking.save()
            
            # Create notification
            Notification.objects.create(
                user=booking.student,
                message=f"Your booking for {booking.computer} has been cancelled by an administrator.",
                notification_type='booking_cancelled',
                booking=booking
            )
            count += 1
        
        messages.success(request, f"{count} bookings cancelled successfully")
    
    return redirect('admin_dashboard')

@login_required
def bulk_cancel_sessions_view(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    if request.method == 'POST':
        # Cancel all upcoming lab sessions
        upcoming_sessions = LabSession.objects.filter(
            is_approved=True,
            end_time__gte=timezone.now()
        )
        
        count = 0
        for session in upcoming_sessions:
            # Create notification before deleting
            Notification.objects.create(
                user=session.lecturer,
                message=f"Your session for {session.lab.name} on {session.start_time.strftime('%Y-%m-%d %H:%M')} has been cancelled by an administrator.",
                notification_type='booking_cancelled',
                lab_session=session
            )
            
            # Delete the session
            session.delete()
            count += 1
        
        messages.success(request, f"{count} lab sessions cancelled successfully")
    
    return redirect('admin_dashboard')

@login_required
def bulk_cancel_recurring_sessions_view(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    if request.method == 'POST':
        # Cancel all recurring sessions
        recurring_sessions = RecurringSession.objects.filter(is_approved=True)
        
        count = 0
        for session in recurring_sessions:
            # Create notification before deleting
            Notification.objects.create(
                user=session.lecturer,
                message=f"Your recurring session '{session.title}' for {session.lab.name} has been cancelled by an administrator.",
                notification_type='recurring_session_rejected',
                recurring_session=session
            )
            
            # Delete all future lab sessions associated with this recurring session
            LabSession.objects.filter(
                lab=session.lab,
                lecturer=session.lecturer,
                title=session.title,
                start_time__gte=timezone.now()
            ).delete()
            
            # Delete the recurring session
            session.delete()
            count += 1
        
        messages.success(request, f"{count} recurring sessions cancelled successfully")
    
    return redirect('admin_dashboard')

@login_required
def reject_booking_view(request, booking_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    booking = get_object_or_404(ComputerBooking, id=booking_id)
    
    # Create notification before cancelling
    Notification.objects.create(
        user=booking.student,
        message=f"Your booking request for {booking.computer} has been rejected.",
        notification_type='booking_rejected',
        booking=booking
    )
    
    # Send rejection email to student
    send_booking_rejection_email(booking)
    
    # Cancel the booking
    booking.is_cancelled = True
    booking.save()
    
    messages.success(request, "Booking rejected successfully and notification email sent")
    return redirect('admin_dashboard')

@login_required
def reject_session_view(request, session_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    session = get_object_or_404(LabSession, id=session_id)
    
    # Create notification before deleting
    Notification.objects.create(
        user=session.lecturer,
        message=f"Your session request for {session.lab.name} has been rejected.",
        notification_type='booking_rejected',
        lab_session=session
    )
    
    # Send rejection email to lecturer
    send_session_rejection_email(session)
    
    # Delete the session
    session.delete()
    
    messages.success(request, "Lab session rejected successfully and notification email sent")
    return redirect('admin_dashboard')

@login_required
def cancel_booking_view(request, booking_id):
    if not request.user.is_admin and not request.user == booking.student:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    booking = get_object_or_404(ComputerBooking, id=booking_id)
    
    if request.method == 'POST':
        booking.is_cancelled = True
        booking.save()
        
        # Create notification and send email
        if request.user.is_admin:
            Notification.objects.create(
                user=booking.student,
                message=f"Your booking for {booking.computer} has been cancelled by an administrator.",
                notification_type='booking_cancelled',
                booking=booking
            )
            # Send cancellation email to student
            send_booking_cancellation_email(booking, cancelled_by="Administrator")
        else:
            # Notify admins when a student cancels
            admin_users = User.objects.filter(is_admin=True)
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    message=f"Booking for {booking.computer} by {booking.student.username} has been cancelled.",
                    notification_type='booking_cancelled',
                    booking=booking
                )
            # Send cancellation email to student
            send_booking_cancellation_email(booking, cancelled_by="Student")
        
        messages.success(request, "Booking cancelled successfully and confirmation email sent")
        return redirect('home')
    
    return render(request, 'cancel_booking.html', {'booking': booking})

@login_required
def cancel_session_view(request, session_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    session = get_object_or_404(LabSession, id=session_id)
    
    if request.method == 'POST':
        # Create notification and send email to lecturer
        Notification.objects.create(
            user=session.lecturer,
            message=f"Your session for {session.lab.name} has been cancelled by an administrator.",
            notification_type='booking_cancelled',
            lab_session=session
        )
        
        # Send cancellation email to lecturer
        send_session_cancellation_email(session, cancelled_by="Administrator")
        
        # Also notify attending students
        for student in session.attending_students.all():
            Notification.objects.create(
                user=student,
                message=f"The lab session '{session.title}' scheduled for {session.lab.name} has been cancelled.",
                notification_type='session_cancelled',
                lab_session=session
            )
        
        # Delete the session
        session.delete()
        
        messages.success(request, "Lab session cancelled successfully and notifications sent")
        return redirect('admin_dashboard')
    
    return render(request, 'cancel_session.html', {'session': session})

@login_required
def rate_student_view(request, student_id, session_id=None, booking_id=None):
    if not request.user.is_admin and not request.user.is_super_admin:
        messages.error(request, "Only administrators can rate students.")
        return redirect('home')
    
    student = get_object_or_404(User, id=student_id, is_student=True)
    session = get_object_or_404(LabSession, id=session_id) if session_id else None
    booking = get_object_or_404(ComputerBooking, id=booking_id) if booking_id else None
    
    # Check if this admin has already rated this student for this session/booking
    if session:
        existing_rating = StudentRating.objects.filter(
            student=student,
            rated_by=request.user,
            session=session
        ).first()
    elif booking:
        existing_rating = StudentRating.objects.filter(
            student=student,
            rated_by=request.user,
            booking=booking
        ).first()
    else:
        messages.error(request, "Either session or booking must be specified.")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        if existing_rating:
            form = StudentRatingForm(request.POST, instance=existing_rating)
        else:
            form = StudentRatingForm(request.POST)
        
        if form.is_valid():
            rating = form.save(commit=False)
            rating.student = student
            rating.rated_by = request.user
            
            if session:
                rating.session = session
            elif booking:
                rating.booking = booking
                
            rating.save()
            
            messages.success(request, f"Rating for {student.get_full_name()} submitted successfully.")
            
            # Redirect back to the appropriate page
            if session:
                return redirect('session_detail', session_id=session.id)
            elif booking:
                return redirect('booking_detail', booking_id=booking.id)
    else:
        form = StudentRatingForm(instance=existing_rating) if existing_rating else StudentRatingForm()
    
    context = {
        'form': form,
        'student': student,
        'session': session,
        'booking': booking,
        'existing_rating': existing_rating,
    }
    
    return render(request, 'rate_student.html', context)

@login_required
@require_GET
def session_details_api(request, session_id):
    """API endpoint to get session details for the modal"""
    try:
        session = LabSession.objects.get(id=session_id)
        attending_students = []
        
        # Get all student bookings for this session
        students = session.attending_students.all()
        for student in students:
            attending_students.append({
                'id': student.id,
                'name': f"{student.salutation} {student.first_name} {student.last_name}".strip(),
                'username': student.username,
                'rating': float(student.average_rating),
                'rating_count': student.total_ratings
            })
            
        data = {
            'id': session.id,
            'title': session.title,
            'lab_name': session.lab.name,
            'lecturer_name': f"{session.lecturer.salutation} {session.lecturer.first_name} {session.lecturer.last_name}".strip(),
            'date': session.start_time.strftime('%B %d, %Y'),
            'start_time': session.start_time.strftime('%H:%M'),
            'end_time': session.end_time.strftime('%H:%M'),
            'is_approved': session.is_approved,
            'description': session.description,
            'students': attending_students
        }
        return JsonResponse(data)
    except LabSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

@login_required
@require_GET
def booking_details_api(request, booking_id):
    """API endpoint to get booking details for the modal"""
    try:
        booking = ComputerBooking.objects.get(id=booking_id)
        
        status = 'Pending'
        status_class = 'bg-yellow-100 text-yellow-800'
        
        if booking.is_cancelled:
            status = 'Cancelled'
            status_class = 'bg-red-100 text-red-800'
        elif booking.is_approved:
            status = 'Approved'
            status_class = 'bg-green-100 text-green-800'
        
        data = {
            'id': booking.id,
            'computer': str(booking.computer),
            'lab_name': booking.computer.lab.name,
            'date': booking.start_time.strftime('%B %d, %Y'),
            'start_time': booking.start_time.strftime('%H:%M'),
            'end_time': booking.end_time.strftime('%H:%M'),
            'booking_code': booking.booking_code,
            'status': status,
            'status_class': status_class,
            'created_at': booking.created_at.strftime('%B %d, %Y %H:%M'),
            'purpose': booking.purpose,
            'student': {
                'id': booking.student.id,
                'name': f"{booking.student.salutation} {booking.student.first_name} {booking.student.last_name}".strip(),
                'username': booking.student.username,
                'school': booking.student.get_school_display() if booking.student.school else 'Not specified',
                'course': booking.student.course,
                'rating': float(booking.student.average_rating),
                'rating_count': booking.student.total_ratings
            }
        }
        return JsonResponse(data)
    except ComputerBooking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)

@login_required
def student_details_view(request, student_id):
    if not request.user.is_admin and not request.user.is_super_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    student = get_object_or_404(User, id=student_id, is_student=True)
    
    # Get recent bookings
    recent_bookings = ComputerBooking.objects.filter(
        student=student
    ).order_by('-start_time')[:10]
    
    # Get ratings
    ratings = StudentRating.objects.filter(
        student=student
    ).order_by('-created_at')
    
    context = {
        'student': student,
        'recent_bookings': recent_bookings,
        'ratings': ratings,
    }
    
    return render(request, 'student_details.html', context)

from django.contrib.auth.mixins import LoginRequiredMixin

class ProfileView(LoginRequiredMixin, TemplateView):
    """View for managing user profile"""
    template_name = 'profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add forms to context
        context['profile_form'] = UserProfileForm(instance=user)
        context['password_form'] = PasswordChangeForm(user)
        
        # Add user profile data
        context['user_bookings'] = user.computer_bookings.all()[:5]
        context['total_bookings'] = user.computer_bookings.count()
        
        if user.is_lecturer:
            context['user_sessions'] = user.booked_sessions.all()[:5]
            context['total_sessions'] = user.booked_sessions.count()
        
        return context
    
    def post(self, request, *args, **kwargs):
        user = request.user
        action = request.POST.get('action')
        
        if action == 'update_profile':
            profile_form = UserProfileForm(request.POST, instance=user)
            
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile was successfully updated!')
                return redirect('profile')
            else:
                # Return form with errors
                context = self.get_context_data()
                context['profile_form'] = profile_form
                return self.render_to_response(context)
        
        elif action == 'change_password':
            password_form = PasswordChangeForm(user, request.POST)
            
            if password_form.is_valid():
                user = password_form.save()
                # Keep the user logged in
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was successfully updated!')
                return redirect('profile')
            else:
                # Return form with errors
                context = self.get_context_data()
                context['password_form'] = password_form
                return self.render_to_response(context)
        
        # Default fallback
        return redirect('profile')

@login_required
def extend_booking(request, booking_id):
    """Extend a booking by 30 minutes"""
    booking = get_object_or_404(ComputerBooking, pk=booking_id, student=request.user)
    
    # Check if booking can be extended
    if not booking.can_be_extended():
        messages.error(request, "Sorry, this booking cannot be extended.")
        return redirect('booking_detail', booking_id=booking.id)
    
    # Process extension
    booking.extend_booking()
    messages.success(request, f"Your booking has been extended by 30 minutes until {booking.end_time.strftime('%H:%M')}")
    
    return redirect('booking_detail', booking_id=booking.id)

@login_required
def unread_notifications_json(request):
    """Return unread notifications as JSON"""
    unread = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')
    
    notifications = []
    for notification in unread:
        notifications.append({
            'id': notification.id,
            'message': notification.message,
            'notification_type': notification.notification_type,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return JsonResponse({
        'count': unread.count(),
        'notifications': notifications
    })

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from src.json_encoders import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from .models import (
    ComputerBooking, LabSession, ComputerBookingAttendance, 
    SessionAttendance, User
)
from .forms import AttendanceForm, BulkAttendanceForm
from django.db.models import Avg

def is_admin(user):
    """Check if user is admin or super admin"""
    return user.is_authenticated and (user.is_admin or user.is_super_admin)

@login_required
@user_passes_test(is_admin)
def admin_check_in_dashboard(request):
    """Dashboard for admins to view and manage check-ins"""
    try:
        # Get date from query params or use today's date
        date_str = request.GET.get('date')
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = timezone.now().date()
        else:
            selected_date = timezone.now().date()
        
        now = timezone.now()
        tomorrow = selected_date + timedelta(days=1)
        
        # Define base queries with select_related for performance
        base_bookings_query = ComputerBooking.objects.filter(
            is_approved=True,
            is_cancelled=False
        ).select_related('student', 'computer', 'computer__lab')
        
        base_sessions_query = LabSession.objects.filter(
            is_approved=True,
        ).select_related('lab', 'lecturer')
        
        # If user is lab-specific admin, filter by their labs
        if request.user.is_admin and not request.user.is_super_admin:
            managed_labs = request.user.managed_labs.all()
            base_bookings_query = base_bookings_query.filter(computer__lab__in=managed_labs)
            base_sessions_query = base_sessions_query.filter(lab__in=managed_labs)
        
        # Get bookings that overlap with the selected date
        today_bookings = base_bookings_query.filter(
            start_time__date__lte=selected_date,
            end_time__date__gte=selected_date
        ).order_by('start_time')
        
        # Get lab sessions for the selected date
        today_sessions = base_sessions_query.filter(
            start_time__date__lte=selected_date,
            end_time__date__gte=selected_date
        ).order_by('start_time')
        
        # Create session_attendance dictionary
        session_attendance = {}
        for session in today_sessions:
            # Get count of students marked as present for this session
            present_count = SessionAttendance.objects.filter(
                session=session,
                status='present'
            ).count()
            session_attendance[session.id] = present_count
        
        # Count attendance stats
        booking_attendance = {
            'total': today_bookings.count(),
            'checked_in': ComputerBookingAttendance.objects.filter(
                booking__in=today_bookings,
                status='present'
            ).count(),
            'absent': ComputerBookingAttendance.objects.filter(
                booking__in=today_bookings,
                status='absent'
            ).count(),
            'late': ComputerBookingAttendance.objects.filter(
                booking__in=today_bookings,
                status='late'
            ).count(),
        }
        
        # Add debugging info for admins
        all_bookings_count = base_bookings_query.count()
        all_sessions_count = base_sessions_query.count()
        
        if all_bookings_count == 0 and all_sessions_count == 0:
            messages.warning(request, "There are no bookings or sessions in the system yet.")
        elif today_bookings.count() == 0 and today_sessions.count() == 0:
            messages.info(request, 
                f"No bookings or sessions scheduled for {selected_date.strftime('%Y-%m-%d')}. "
                f"There are {all_bookings_count} total bookings and {all_sessions_count} total sessions in the system."
            )
        
        context = {
            'today_bookings': today_bookings,
            'today_sessions': today_sessions,
            'booking_attendance': booking_attendance,
            'session_attendance': session_attendance,  # Add this for session attendance counts
            'today': selected_date,
            'tomorrow': tomorrow,
            'now': now,
            'all_bookings_count': all_bookings_count,
            'all_sessions_count': all_sessions_count,
            'debug_info': {
                'today': selected_date.isoformat() if selected_date else None,
                'now': now.isoformat(),
                'today_bookings_count': today_bookings.count(),
                'today_sessions_count': today_sessions.count(),
                'sample_bookings': [
                    {
                        'id': b.id,
                        'student': b.student.username,
                        'start': b.start_time.isoformat(),
                        'end': b.end_time.isoformat(),
                    } for b in today_bookings[:3]
                ],
                'sample_sessions': [
                    {
                        'id': s.id,
                        'title': s.title,
                        'start': s.start_time.isoformat(),
                        'end': s.end_time.isoformat(),
                    } for s in today_sessions[:3]
                ]
            }
        }
        
        return render(request, 'check_in_dashboard.html', context)
        
    except Exception as e:
        # Log unexpected errors
        import traceback
        traceback.print_exc()
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('home')

@login_required
@user_passes_test(is_admin)
def computer_booking_check_in(request, booking_id):
    """View for checking in a student for a computer booking"""
    booking = get_object_or_404(ComputerBooking, id=booking_id)
    
    # Check if admin has permission for this lab
    if (request.user.is_admin and not request.user.is_super_admin and 
            booking.computer.lab not in request.user.managed_labs.all()):
        messages.error(request, "You don't have permission to manage attendance for this lab")
        return redirect('admin_check_in_dashboard')
    
    # Get or initialize attendance
    try:
        attendance = booking.attendance
    except ComputerBookingAttendance.DoesNotExist:
        attendance = None
    
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.booking = booking
            attendance.checked_by = request.user
            
            # Set check-in time if not already set
            if not attendance.check_in_time and form.cleaned_data['status'] in ['present', 'late']:
                attendance.check_in_time = timezone.now()
            
            attendance.save()
            
            # Create notification
            Notification.objects.create(
                user=booking.student,
                message=f"Your attendance for booking at {booking.computer} has been marked as {attendance.get_status_display()}",
                notification_type='attendance_marked' if not attendance.pk else 'attendance_updated',
                booking=booking
            )
            
            messages.success(request, f"Attendance for {booking.student.get_full_name()} has been recorded")
            return redirect('admin_check_in_dashboard')
    else:
        initial_data = {}
        # Auto-mark as late if arriving after start time + 10 min grace period
        if not attendance and booking.start_time + timedelta(minutes=10) < timezone.now():
            initial_data['status'] = 'late'
        
        form = AttendanceForm(instance=attendance, initial=initial_data)
    
    context = {
        'booking': booking,
        'form': form,
        'attendance': attendance
    }
    
    return render(request, 'computer_booking_check_in.html', context)

@login_required
@user_passes_test(is_admin)
def lab_session_attendance(request, session_id):
    """View for managing attendance for a lab session"""
    session = get_object_or_404(LabSession, id=session_id)
    
    # Check if admin has permission for this lab
    if (request.user.is_admin and not request.user.is_super_admin and 
            session.lab not in request.user.managed_labs.all()):
        messages.error(request, "You don't have permission to manage attendance for this lab")
        return redirect('admin_check_in_dashboard')
    
    # Get existing attendance records
    attendance_records = SessionAttendance.objects.filter(session=session)
    
    # Get all students who are supposed to attend
    attending_students = session.attending_students.all()
    
    # For students without attendance records, create placeholders
    attendance_dict = {record.student_id: record for record in attendance_records}
    
    students_data = []
    for student in attending_students:
        attendance = attendance_dict.get(student.id)
        students_data.append({
            'student': student,
            'attendance': attendance,
            'status': attendance.status if attendance else 'absent',
            'check_in_time': attendance.check_in_time if attendance else None,
        })
    
    if request.method == 'POST':
        # Process bulk attendance form
        form = BulkAttendanceForm(request.POST)
        if form.is_valid():
            # Extract student IDs and statuses from form
            student_ids = request.POST.getlist('student_id')
            statuses = request.POST.getlist('status')
            notes = request.POST.getlist('notes')
            
            # Process each student's attendance
            for i, student_id in enumerate(student_ids):
                try:
                    student = User.objects.get(id=student_id)
                    status = statuses[i]
                    note = notes[i] if i < len(notes) else ''
                    
                    # Record attendance
                    session.record_student_attendance(
                        student=student,
                        status=status,
                        admin_user=request.user,
                        notes=note
                    )
                except (User.DoesNotExist, IndexError):
                    continue
            
            messages.success(request, f"Attendance recorded for {len(student_ids)} students")
            return redirect('admin_check_in_dashboard')
    else:
        # Initialize form
        form = BulkAttendanceForm()
    
    context = {
        'session': session,
        'students_data': students_data,
        'form': form
    }
    
    return render(request, 'lab_session_attendance.html', context)

@login_required
@user_passes_test(is_admin)
@require_POST
def quick_check_in(request, booking_id):
    """API endpoint for quickly checking in a student without additional info"""
    booking = get_object_or_404(ComputerBooking, id=booking_id)
    
    # Check if admin has permission for this lab
    if (request.user.is_admin and not request.user.is_super_admin and 
            booking.computer.lab not in request.user.managed_labs.all()):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        
    status = request.POST.get('status', 'present')
    notes = request.POST.get('notes', '')
    
    attendance = booking.mark_attendance(
        status=status,
        admin_user=request.user,
        check_in_time=timezone.now(),
        notes=notes
    )
    
    return JsonResponse({
        'status': 'success', 
        'attendance': {
            'status': attendance.status,
            'status_display': attendance.get_status_display(),
            'check_in_time': attendance.check_in_time.strftime('%H:%M')
        }
    })

@login_required
def cancel_computer_booking(request, booking_id):
    """View for a student to cancel their computer booking"""
    booking = get_object_or_404(ComputerBooking, id=booking_id, student=request.user)
    
    # Check if booking can be cancelled
    if not booking.is_approved or booking.is_cancelled:
        messages.error(request, "This booking cannot be cancelled. It may be already cancelled or not approved yet.")
        return redirect('booking_detail', booking_id=booking.id)
        
    # Check if booking is starting soon (within 30 minutes)
    if booking.start_time <= (timezone.now() + timedelta(minutes=30)):
        messages.error(request, "Bookings can only be cancelled at least 30 minutes before the start time.")
        return redirect('booking_detail', booking_id=booking.id)
    
    if request.method == 'POST':
        cancellation_reason = request.POST.get('reason', '')
        
        if booking.cancel_booking(reason=cancellation_reason):
            messages.success(request, "Your booking has been successfully cancelled.")
            return redirect('my_bookings')
        else:
            messages.error(request, "Could not cancel the booking. Please try again or contact support.")
    
    return render(request, 'cancel_booking.html', {'booking': booking})

@login_required
def cancel_lab_session(request, session_id):
    """View for a lecturer to cancel their lab session"""
    session = get_object_or_404(LabSession, id=session_id, lecturer=request.user)
    
    # Check if session can be cancelled
    if not session.is_approved or session.is_cancelled:
        messages.error(request, "This session cannot be cancelled. It may be already cancelled or not approved yet.")
        return redirect('session_detail', session_id=session.id)
        
    # Check if session is starting soon (within 2 hours)
    if session.start_time <= (timezone.now() + timedelta(hours=2)):
        messages.error(request, "Sessions can only be cancelled at least 2 hours before the start time.")
        return redirect('session_detail', session_id=session.id)
    
    if request.method == 'POST':
        cancellation_reason = request.POST.get('reason', '')
        
        if session.cancel_session(reason=cancellation_reason):
            messages.success(request, "Your lab session has been successfully cancelled.")
            return redirect('my_sessions')
        else:
            messages.error(request, "Could not cancel the session. Please try again or contact support.")
    
    return render(request, 'cancel_session.html', {'session': session})

def booking_detail(request, booking_id):
    booking = get_object_or_404(ComputerBooking, id=booking_id)
    
    # Add this:
    now = timezone.now()
    now_plus_30min = now + timedelta(minutes=30)
    
    context = {
        'booking': booking,
        'now': now,
        'now_plus_30min': now_plus_30min,
    }
    return render(request, 'booking_detail.html', context)

def session_detail(request, session_id):
    session = get_object_or_404(LabSession, id=session_id)
    
    # Add this:
    now = timezone.now()
    now_plus_2hr = now + timedelta(hours=2)
    
    context = {
        'session': session,
        'now': now,
        'now_plus_2hr': now_plus_2hr,
    }
    return render(request, 'session_detail.html', context)

@login_required
def booking_history_view(request):
    """View for showing a user's booking history"""
    
    # Get the current user's bookings
    computer_bookings = ComputerBooking.objects.filter(
        student=request.user
    ).order_by('-start_time')
    
    # If the user is a lecturer, get their lab sessions too
    lab_sessions = []
    if hasattr(request.user, 'is_lecturer') and request.user.is_lecturer:
        lab_sessions = LabSession.objects.filter(
            lecturer=request.user
        ).order_by('-start_time')
    
    # For past bookings/sessions
    past_computer_bookings = computer_bookings.filter(
        end_time__lt=timezone.now()
    )
    
    past_lab_sessions = []
    if hasattr(request.user, 'is_lecturer') and request.user.is_lecturer:
        past_lab_sessions = lab_sessions.filter(
            end_time__lt=timezone.now()
        )
    
    return render(request, 'booking_history.html', {
        'current_computer_bookings': computer_bookings.filter(
            end_time__gte=timezone.now(),
            is_cancelled=False
        ),
        'past_computer_bookings': past_computer_bookings,
        'current_lab_sessions': lab_sessions.filter(
            end_time__gte=timezone.now(),
            is_cancelled=False
        ) if lab_sessions else [],
        'past_lab_sessions': past_lab_sessions,
    })

@login_required
@user_passes_test(is_admin)
def assign_student_view(request):
    """View for admins to assign students to sessions or computers"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method")
        return redirect('admin_dashboard')
    
    student_id = request.POST.get('student_id')
    assignment_type = request.POST.get('assignment_type')
    purpose = request.POST.get('purpose', '')
    
    try:
        student = User.objects.get(id=student_id, is_student=True)
    except User.DoesNotExist:
        messages.error(request, "Student not found")
        return redirect('admin_dashboard')
    
    if assignment_type == 'lab_session':
        # Assign student to lab session
        session_id = request.POST.get('lab_session_id')
        try:
            session = LabSession.objects.get(id=session_id)
            
            # Add student to the session
            session.attending_students.add(student)
            
            # Create notification for the student
            Notification.objects.create(
                user=student,
                message=f"You have been assigned to the lab session: {session.title} on {session.start_time.strftime('%Y-%m-%d %H:%M')}",
                notification_type='session_booked',
                lab_session=session
            )
            
            messages.success(request, f"Successfully assigned {student.get_full_name()} to {session.title}")
            
        except LabSession.DoesNotExist:
            messages.error(request, "Lab session not found")
            
    elif assignment_type == 'computer_booking':
        # Create a computer booking for the student
        computer_id = request.POST.get('computer_id')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        
        try:
            computer = Computer.objects.get(id=computer_id)
            start_time = timezone.make_aware(datetime.fromisoformat(start_time_str))
            end_time = timezone.make_aware(datetime.fromisoformat(end_time_str))
            
            # Create new booking
            booking = ComputerBooking.objects.create(
                computer=computer,
                student=student,
                start_time=start_time,
                end_time=end_time,
                purpose=purpose,
                is_approved=True  # Admin-created bookings are auto-approved
            )
            
            # Create notification for the student
            Notification.objects.create(
                user=student,
                message=f"A computer has been booked for you: {computer} on {start_time.strftime('%Y-%m-%d %H:%M')}",
                notification_type='booking_approved',
                booking=booking
            )
            
            messages.success(request, f"Successfully booked {computer} for {student.get_full_name()}")
            
        except Computer.DoesNotExist:
            messages.error(request, "Computer not found")
        except ValueError:
            messages.error(request, "Invalid date/time format")
        except ValidationError as e:
            messages.error(request, f"Booking validation error: {str(e)}")
    
    else:
        messages.error(request, "Invalid assignment type")
    
    return redirect('admin_dashboard')

@login_required
@require_GET
def lab_computers_api(request, lab_id):
    """API endpoint to get computers for a lab"""
    try:
        lab = Lab.objects.get(id=lab_id)
        computers = Computer.objects.filter(lab=lab)
        
        data = {
            'lab_id': lab.id,
            'lab_name': lab.name,
            'computers': [
                {
                    'id': computer.id,
                    'number': computer.computer_number,
                    'specs': computer.specs,
                    'status': computer.status
                } for computer in computers
            ]
        }
        return JsonResponse(data)
    except Lab.DoesNotExist:
        return JsonResponse({'error': 'Lab not found'}, status=404)
    
@login_required
@user_passes_test(is_admin)
def student_bookings_api(request, student_id):
    """API endpoint to get a student's computer bookings"""
    try:
        student = get_object_or_404(User, id=student_id, is_student=True)
        bookings = ComputerBooking.objects.filter(
            student=student, 
            is_approved=True,
            is_cancelled=False
        ).order_by('-start_time')[:20]
        
        data = {
            'bookings': [
                {
                    'id': booking.id,
                    'start_time': booking.start_time.isoformat(),
                    'end_time': booking.end_time.isoformat(),
                    'computer_number': booking.computer.computer_number,
                    'lab_name': booking.computer.lab.name
                } for booking in bookings
            ]
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@user_passes_test(is_admin)
def student_sessions_api(request, student_id):
    """API endpoint to get a student's lab sessions"""
    try:
        student = get_object_or_404(User, id=student_id, is_student=True)
        sessions = LabSession.objects.filter(
            attending_students=student,
            is_approved=True
        ).order_by('-start_time')[:20]
        
        data = {
            'sessions': [
                {
                    'id': session.id,
                    'title': session.title,
                    'start_time': session.start_time.isoformat(),
                    'end_time': session.end_time.isoformat(),
                    'lab_name': session.lab.name
                } for session in sessions
            ]
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@user_passes_test(is_admin)
@require_POST
def rate_student_ajax(request):
    """AJAX endpoint for rating a student"""
    try:
        student_id = request.POST.get('student_id')
        rating_type = request.POST.get('rating_type')
        
        # Fix: Get the score parameter and check if it exists
        score_value = request.POST.get('score')
        if not score_value:
            return JsonResponse({'success': False, 'error': 'No score provided'}, status=400)
        
        score = int(score_value)
        comment = request.POST.get('comment', '')
        
        student = get_object_or_404(User, id=student_id, is_student=True)
        
        if rating_type == 'booking':
            booking_id = request.POST.get('booking_id')
            if not booking_id:
                return JsonResponse({'success': False, 'error': 'No booking selected'}, status=400)
                
            booking = get_object_or_404(ComputerBooking, id=booking_id)
            
            # Create rating for booking
            StudentRating.objects.create(
                student=student,
                rated_by=request.user,
                score=score,  # Changed from 'rating' to 'score' to match model
                comment=comment,
                booking=booking,
                session=None  # Explicitly set the other field to None
            )
            
        elif rating_type == 'session':
            session_id = request.POST.get('session_id')
            if not session_id:
                return JsonResponse({'success': False, 'error': 'No session selected'}, status=400)
                
            session = get_object_or_404(LabSession, id=session_id)
            
            # Create rating for session
            StudentRating.objects.create(
                student=student,
                rated_by=request.user,
                score=score,  # Changed from 'rating' to 'score' to match model
                comment=comment,
                session=session,
                booking=None  # Explicitly set the other field to None
            )
            
        else:
            return JsonResponse({'success': False, 'error': 'Invalid rating type'}, status=400)
        
        # Calculate new average rating
        from django.db.models import Avg
        avg_rating = StudentRating.objects.filter(student=student).aggregate(Avg('score'))['score__avg']
        
        return JsonResponse({
            'success': True,
            'message': 'Rating submitted successfully',
            'new_rating': avg_rating
        })
        
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid score value'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)