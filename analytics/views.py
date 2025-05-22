from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q, Avg, ExpressionWrapper, F
from django.db.models.functions import TruncDay, TruncWeek
from django.contrib import messages
from datetime import timedelta, datetime
import json
from .models import User, SystemEvent, ComputerBooking, LabSession, Computer
from django.shortcuts import redirect
from django.db import models
from django.db.models import fields
from django.db.models import Q

# Create your views here.
@login_required
def analytics_dashboard_view(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    # Time period filters
    period = request.GET.get('period', 'month')  # Default to month
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'quarter':
        start_date = today - timedelta(days=90)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)  # Default to month
    
    # User Activity & Engagement
    user_counts = User.objects.aggregate(
        total=Count('id'),
        students=Count('id', filter=Q(is_student=True)),
        lecturers=Count('id', filter=Q(is_lecturer=True)),
        admins=Count('id', filter=Q(is_admin=True))
    )
    
    # Active users (logged in during the period)
    active_users = SystemEvent.objects.filter(
        event_type='login',
        timestamp__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ).values('user').distinct().count()
    
    # Logins per day/week/month
    if period == 'week':
        login_trend = SystemEvent.objects.filter(
            event_type='login',
            timestamp__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        ).annotate(
            date=TruncDay('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
    elif period == 'month' or period == 'quarter':
        login_trend = SystemEvent.objects.filter(
            event_type='login',
            timestamp__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        ).annotate(
            date=TruncDay('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
    else:  # year
        login_trend = SystemEvent.objects.filter(
            event_type='login',
            timestamp__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        ).annotate(
            date=TruncWeek('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
    
    # Format for charts
    login_dates = [item['date'].strftime('%Y-%m-%d') for item in login_trend]
    login_counts = [item['count'] for item in login_trend]
    
    # New user registrations
    new_users = SystemEvent.objects.filter(
        event_type='registration',
        timestamp__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ).count()
    
    # Role-based login activity
    role_activity = SystemEvent.objects.filter(
        event_type='login',
        timestamp__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ).values('user__is_student', 'user__is_lecturer', 'user__is_admin').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Booking Analytics
    total_bookings = ComputerBooking.objects.filter(
        created_at__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ).count()
    
    total_sessions = LabSession.objects.filter(
        created_at__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ).count()
    
    # Most booked time slots (hour of day)
    booking_hours = ComputerBooking.objects.extra(
    select={'hour': "EXTRACT(hour FROM start_time)"}
).values('hour').annotate(
    count=Count('id')
).order_by('hour')
    
    # Most booked labs
    popular_labs = LabSession.objects.filter(
        created_at__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ).values('lab__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Computer reservation frequency
    popular_computers = ComputerBooking.objects.filter(
        created_at__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ).values('computer__computer_number', 'computer__lab__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Approval metrics
    approval_time = {'avg_approval_time': None}  # Temporary fix
    
    # Booking rejection rate
    booking_rejection_rate = ComputerBooking.objects.filter(
        created_at__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ).aggregate(
        total=Count('id'),
        rejected=Count('id', filter=Q(is_approved=False, is_cancelled=True)),
        cancelled=Count('id', filter=Q(is_cancelled=True)),
    )
    
    # Equipment Usage
    total_devices = Computer.objects.count()
    
    # Computers by status
    computer_status = Computer.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Maintenance metrics
    computers_in_maintenance = Computer.objects.filter(status='maintenance').count()
    
    # System operations
    admin_response_time = SystemEvent.objects.filter(
        event_type__in=['booking_approved', 'booking_rejected', 'session_approved', 'session_rejected'],
        timestamp__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ).annotate(
        response_time=ExpressionWrapper(
            F('timestamp') - F('details__request_time'),
            output_field=fields.DurationField()
        )
    ).aggregate(
        avg_response_time=Avg('response_time')
    )
    
    # Format chart data
    lab_names = [lab['lab__name'] for lab in popular_labs]
    lab_booking_counts = [lab['count'] for lab in popular_labs]
    
    context = {
        'period': period,
        'user_counts': user_counts,
        'active_users': active_users,
        'new_users': new_users,
        'login_dates': json.dumps(login_dates),
        'login_counts': json.dumps(login_counts),
        'role_activity': role_activity,
        'total_bookings': total_bookings,
        'total_sessions': total_sessions,
        'booking_hours': booking_hours,
        'popular_labs': popular_labs,
        'lab_names': json.dumps(lab_names),
        'lab_booking_counts': json.dumps(lab_booking_counts),
        'popular_computers': popular_computers,
        'approval_time': approval_time,
        'booking_rejection_rate': booking_rejection_rate,
        'total_devices': total_devices,
        'computer_status': computer_status,
        'computers_in_maintenance': computers_in_maintenance,
        'admin_response_time': admin_response_time,
    }
    
    return render(request, 'analytics_dashboard.html', context)