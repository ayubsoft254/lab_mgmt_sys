from django.forms import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse
from .models import Lab, Computer, ComputerBooking, LabSession, Notification, User, RecurringSession
from datetime import datetime, timedelta
from .forms import ComputerBookingForm, LabSessionForm, CustomUserCreationForm, RecurringSessionForm


def landing(request):
    return render(request, 'landing.html')

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
            
            # Notify admin about new booking
            admin_users = User.objects.filter(is_admin=True)
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    message=f"New computer booking: {booking.computer} by {request.user.username}",
                    notification_type='new_booking'
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
                
                # Notify admin about new session booking
                admin_users = User.objects.filter(is_admin=True)
                for admin in admin_users:
                    Notification.objects.create(
                        user=admin,
                        message=f"New lab session request: {session.lab.name} by {request.user.username}",
                        notification_type='session_booked'
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
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
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
        'total_pending_approvals': pending_computer_bookings.count() + pending_lab_sessions.count(),
    }
    
    labs = Lab.objects.all()
    
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
    })

@login_required
def approve_booking_view(request, booking_id):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    booking = get_object_or_404(ComputerBooking, id=booking_id)
    booking.is_approved = True
    booking.save()
    
    # Notify student about approval
    Notification.objects.create(
        user=booking.student,
        message=f"Your booking for {booking.computer} has been approved.",
        notification_type='booking_approved'
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
    session.save()  # This will trigger the save method that handles conflicts
    
    # Notify lecturer about approval
    Notification.objects.create(
        user=session.lecturer,
        message=f"Your session for {session.lab.name} has been approved.",
        notification_type='booking_approved'
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
                
                # Notify admin about new recurring session request
                admin_users = User.objects.filter(is_admin=True)
                for admin in admin_users:
                    Notification.objects.create(
                        user=admin,
                        message=f"New recurring session request: {recurring_session.lab.name} - {recurring_session.title}",
                        notification_type='recurring_session_booked'
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
        
        messages.success(request, "Recurring session cancelled successfully")
        return redirect('recurring_sessions_list')
    
    return render(request, 'cancel_recurring_session.html', {
        'recurring_session': recurring_session
    })