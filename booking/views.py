from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from datetime import datetime, timedelta

from .models import (
    User, Lab, Computer, ComputerBooking, LabSession, 
    Notification, RecurringSession, StudentRating, ComputerBookingAttendance, 
    SessionAttendance
)
from .forms import (
    ComputerBookingForm, LabSessionForm, RecurringSessionForm, 
    StudentRatingForm, UserProfileForm, AttendanceForm, BulkAttendanceForm
)
 
class LandingPageView(TemplateView):
    template_name = 'landing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics for the landing page
        context['active_students'] = User.objects.filter(is_student=True).count()
        context['lab_count'] = Lab.objects.count()
        
        # Calculate system uptime percentage (this is an example - you might want to use a real metric)
        # For demonstration, we'll use a calculation based on successful bookings vs. total
        total_bookings = ComputerBooking.objects.count()
        successful_bookings = ComputerBooking.objects.filter(is_approved=True).count()
        if total_bookings > 0:
            uptime_percentage = round((successful_bookings / total_bookings) * 100)
        else:
            uptime_percentage = 100  # Default if no bookings yet
        
        # Ensure the percentage is reasonable
        uptime_percentage = min(max(uptime_percentage, 95), 99.9)  # Between 95% and 99.9%
        context['uptime_percentage'] = uptime_percentage
        
        # Get total hours of lab usage in the past month
        one_month_ago = timezone.now() - timedelta(days=30)
        
        # Sum duration of all bookings in the past month
        recent_bookings = ComputerBooking.objects.filter(
            start_time__gte=one_month_ago,
            is_approved=True
        )
        
        total_hours = 0
        for booking in recent_bookings:
            duration = booking.end_time - booking.start_time
            total_hours += duration.total_seconds() / 3600  # Convert seconds to hours
        
        context['total_hours'] = int(total_hours)
        
        return context

@login_required
def home_view(request):
    upcoming_bookings = None
    upcoming_sessions = None
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
    
    labs = Lab.objects.all()
    
    return render(request, 'home.html', {
        'labs': labs,
        'upcoming_bookings': upcoming_bookings,
        'upcoming_sessions': upcoming_sessions,
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
            
            # Check if there's a lab session during this time
            conflicting_sessions = LabSession.objects.filter(
                lab=lab,
                is_approved=True,
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time
            )
            
            if conflicting_sessions.exists():
                messages.error(request, "Lab is reserved for a session during this time slot")
                return render(request, 'student_booking.html', {'form': form, 'lab': lab})
            
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
    ).order_by('start_time')
    
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
    
    return render(request, 'admin_dashboard.html', {
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
    })

@login_required
def approve_booking_view(request, booking_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    booking = get_object_or_404(ComputerBooking, id=booking_id)
    booking.is_approved = True
    booking.save()
    
    # Updated notification with proper reference
    Notification.objects.create(
        user=booking.student,
        message=f"Your booking for {booking.computer} has been approved.",
        notification_type='booking_approved',
        booking=booking  # Add direct reference
    )
    
    messages.success(request, "Booking approved successfully")
    return redirect('admin_dashboard')

@login_required
def approve_session_view(request, session_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    session = get_object_or_404(LabSession, id=session_id)
    session.is_approved = True
    session.save()
    
    # Updated notification with proper reference
    Notification.objects.create(
        user=session.lecturer,
        message=f"Your session for {session.lab.name} has been approved.",
        notification_type='booking_approved',
        lab_session=session  # Add direct reference
    )
    
    messages.success(request, "Lab session approved successfully")
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
    # Determine the scope of the search (lab-wide or computer-specific)
    if computer_id:
        computer = get_object_or_404(Computer, id=computer_id)
        lab = computer.lab
    elif lab_id:
        lab = get_object_or_404(Lab, id=lab_id)
        computer = None
    else:
        # If no specific lab or computer is selected, return an error
        return render(request, 'free_timeslots.html', {
            'error': 'Please select a lab or computer'
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
            slot_start = timezone.make_aware(datetime.combine(current_date, datetime.min.replace(hour=hour)))
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
            
            time_slots.append({
                'date': current_date,
                'start_time': slot_start,
                'end_time': slot_end,
                'is_free': is_free
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
            count += 1
        
        messages.success(request, f"{count} bookings approved successfully")
    
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
            count += 1
        
        messages.success(request, f"{count} lab sessions approved successfully")
    
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
    
    # Cancel the booking
    booking.is_cancelled = True
    booking.save()
    
    messages.success(request, "Booking rejected successfully")
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
    
    # Delete the session
    session.delete()
    
    messages.success(request, "Lab session rejected successfully")
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
        
        # Create notification
        if request.user.is_admin:
            Notification.objects.create(
                user=booking.student,
                message=f"Your booking for {booking.computer} has been cancelled by an administrator.",
                notification_type='booking_cancelled',
                booking=booking
            )
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
        
        messages.success(request, "Booking cancelled successfully")
        return redirect('home')
    
    return render(request, 'cancel_booking.html', {'booking': booking})

@login_required
def cancel_session_view(request, session_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    session = get_object_or_404(LabSession, id=session_id)
    
    if request.method == 'POST':
        # Create notification before deleting
        Notification.objects.create(
            user=session.lecturer,
            message=f"Your session for {session.lab.name} has been cancelled by an administrator.",
            notification_type='booking_cancelled',
            lab_session=session
        )
        
        # Delete the session
        session.delete()
        
        messages.success(request, "Lab session cancelled successfully")
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
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from .models import (
    ComputerBooking, LabSession, ComputerBookingAttendance, 
    SessionAttendance, User
)
from .forms import AttendanceForm, BulkAttendanceForm

def is_admin(user):
    """Check if user is admin or super admin"""
    return user.is_authenticated and (user.is_admin or user.is_super_admin)

@login_required
@user_passes_test(is_admin)
def admin_check_in_dashboard(request):
    """Dashboard for admins to view and manage check-ins"""
    # Get today's date
    today = timezone.now().date()
    
    # Get today's computer bookings
    today_bookings = ComputerBooking.objects.filter(
        start_time__date=today,
        is_approved=True,
        is_cancelled=False
    ).order_by('start_time')
    
    # Get today's lab sessions
    today_sessions = LabSession.objects.filter(
        start_time__date=today,
        is_approved=True
    ).order_by('start_time')
    
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
    
    # If user is lab-specific admin, filter by their labs
    if request.user.is_admin and not request.user.is_super_admin:
        managed_labs = request.user.managed_labs.all()
        today_bookings = today_bookings.filter(computer__lab__in=managed_labs)
        today_sessions = today_sessions.filter(lab__in=managed_labs)
    
    context = {
        'today_bookings': today_bookings,
        'today_sessions': today_sessions,
        'booking_attendance': booking_attendance,
        'today': today,
        'now': timezone.now()
    }
    
    return render(request, 'check_in_dashboard.html', context)

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