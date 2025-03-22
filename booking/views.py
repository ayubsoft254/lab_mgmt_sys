from django.forms import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse
from .models import Lab, Computer, ComputerBooking, LabSession, Notification, User
from .forms import ComputerBookingForm, LabSessionForm, CustomUserCreationForm

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

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
    
    pending_computer_bookings = ComputerBooking.objects.filter(
        is_approved=False,
        is_cancelled=False,
        end_time__gte=timezone.now()
    ).order_by('start_time')
    
    pending_lab_sessions = LabSession.objects.filter(
        is_approved=False,
        end_time__gte=timezone.now()
    ).order_by('start_time')
    
    labs = Lab.objects.all()
    
    return render(request, 'admin_dashboard.html', {
        'pending_computer_bookings': pending_computer_bookings,
        'pending_lab_sessions': pending_lab_sessions,
        'labs': labs
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