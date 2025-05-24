from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Q, Avg, F, DurationField, ExpressionWrapper
from django.db.models.functions import TruncDay, TruncWeek, TruncDate
from datetime import timedelta, datetime
import json

from booking.models import ComputerBooking, LabSession, Computer, User
from .models import SystemEvent


@login_required
def analytics_dashboard_view(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    # Time period filter
    period = request.GET.get('period', 'month')
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
        start_date = today - timedelta(days=30)

    # Use once
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    # User Activity Summary
    user_counts = User.objects.aggregate(
        total=Count('id'),
        students=Count('id', filter=Q(is_student=True)),
        lecturers=Count('id', filter=Q(is_lecturer=True)),
        admins=Count('id', filter=Q(is_admin=True))
    )

    # Active Users (logged in)
    active_users = SystemEvent.objects.filter(
        event_type='login',
        timestamp__gte=start_datetime
    ).values('user').distinct().count()

    # Login Trend
    trunc_func = TruncDate if period in ['week', 'month', 'quarter'] else TruncWeek

    login_trend = SystemEvent.objects.filter(
        event_type='login',
        timestamp__gte=start_datetime
    ).annotate(
        date=trunc_func('timestamp')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    login_dates = [item['date'].strftime('%Y-%m-%d') for item in login_trend]
    login_counts = [item['count'] for item in login_trend]

    # New Registrations
    new_users = SystemEvent.objects.filter(
        event_type='registration',
        timestamp__gte=start_datetime
    ).count()

    # Role-based login activity
    raw_role_activity = SystemEvent.objects.filter(
        event_type='login',
        timestamp__gte=start_datetime
    ).values('user__is_student', 'user__is_lecturer', 'user__is_admin').annotate(
        count=Count('id')
    ).order_by('-count')

    role_activity = []
    for r in raw_role_activity:
        if r['user__is_admin']:
            role = 'Admin'
        elif r['user__is_lecturer']:
            role = 'Lecturer'
        elif r['user__is_student']:
            role = 'Student'
        else:
            role = 'Unknown'
        role_activity.append({'role': role, 'count': r['count']})

    # Booking stats
    total_bookings = ComputerBooking.objects.filter(created_at__gte=start_datetime).count()
    total_sessions = LabSession.objects.filter(created_at__gte=start_datetime).count()

    # Most booked hours
    booking_hours = []
    try:
        booking_hours = ComputerBooking.objects.extra(
            select={'hour': "EXTRACT(hour FROM start_time)"}
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
    except Exception:
        booking_hours = []  # or fallback method if needed

    # Most booked labs
    popular_labs = LabSession.objects.filter(
        created_at__gte=start_datetime
    ).values('lab__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]

    lab_names = [lab['lab__name'] for lab in popular_labs]
    lab_booking_counts = [lab['count'] for lab in popular_labs]

    # Most booked computers
    popular_computers = ComputerBooking.objects.filter(
        created_at__gte=start_datetime
    ).select_related('computer', 'computer__lab').values(
        'computer__computer_number', 'computer__lab__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # Booking rejection rate
    booking_rejection_rate = ComputerBooking.objects.filter(
        created_at__gte=start_datetime
    ).aggregate(
        total=Count('id'),
        rejected=Count('id', filter=Q(is_approved=False, is_cancelled=True)),
        cancelled=Count('id', filter=Q(is_cancelled=True)),
    )

    # Total computers
    total_devices = Computer.objects.count()

    # Computer status breakdown
    computer_status = Computer.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    # Maintenance count
    computers_in_maintenance = Computer.objects.filter(status='maintenance').count()

    # Admin response time (handle request_time manually if not in DB)
    admin_response_time = {'avg_response_time': None}
    try:
        response_events = SystemEvent.objects.filter(
            event_type__in=[
                'booking_approved', 'booking_rejected',
                'session_approved', 'session_rejected'
            ],
            timestamp__gte=start_datetime
        ).exclude(details__request_time=None)

        annotated = [
            (event.timestamp - timezone.make_aware(datetime.fromisoformat(event.details['request_time'])))
            for event in response_events if 'request_time' in event.details
        ]

        if annotated:
            avg_response = sum(annotated, timedelta()) / len(annotated)
            admin_response_time['avg_response_time'] = avg_response
    except Exception:
        pass

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
        'approval_time': admin_response_time,
        'booking_rejection_rate': booking_rejection_rate,
        'total_devices': total_devices,
        'computer_status': computer_status,
        'computers_in_maintenance': computers_in_maintenance,
        'admin_response_time': admin_response_time,
    }

    return render(request, 'analytics_dashboard.html', context)