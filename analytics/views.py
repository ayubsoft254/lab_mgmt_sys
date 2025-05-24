from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from .models import SystemEvent
from booking.models import ComputerBookingAttendance, SessionAttendance, ComputerBooking, LabSession
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test


class AnalyticsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Enhanced analytics view for system events with comprehensive data"""
    template_name = 'analytics_dashboard.html'
    permission_required = 'system_events.view_systemevent'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request or default to last 30 days
        days = int(self.request.GET.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Base queryset for the selected period
        events_qs = SystemEvent.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        # Key metrics
        context.update({
            'total_events': events_qs.count(),
            'critical_events': events_qs.filter(severity=SystemEvent.SeverityLevels.CRITICAL).count(),
            'unresolved_events': events_qs.filter(resolved=False).count(),
            'security_events': events_qs.filter(
                event_type__in=['LOGIN_FAILED', 'UNAUTHORIZED_ACCESS', 'PERMISSION_DENIED']
            ).count(),
            'days': days,
            'start_date': start_date,
            'end_date': end_date,
        })
        
        # Events by type
        events_by_type = list(events_qs.values('event_type').annotate(
            count=Count('id')
        ).order_by('-count'))
        
        # Events by severity
        events_by_severity = list(events_qs.values('severity').annotate(
            count=Count('id')
        ).order_by('-count'))
        
        # Daily events for the last 30 days
        daily_events = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_events = events_qs.filter(
                timestamp__gte=day_start,
                timestamp__lt=day_end
            )
            
            daily_events.append({
                'date': day.strftime('%Y-%m-%d'),
                'total': day_events.count(),
                'critical': day_events.filter(severity=SystemEvent.SeverityLevels.CRITICAL).count(),
                'high': day_events.filter(severity=SystemEvent.SeverityLevels.HIGH).count(),
                'medium': day_events.filter(severity=SystemEvent.SeverityLevels.MEDIUM).count(),
                'low': day_events.filter(severity=SystemEvent.SeverityLevels.LOW).count(),
            })
        
        # Hourly distribution (last 24 hours)
        hourly_events = []
        last_24h = timezone.now() - timedelta(hours=24)
        for hour in range(24):
            hour_start = last_24h.replace(minute=0, second=0, microsecond=0) + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            
            hourly_count = SystemEvent.objects.filter(
                timestamp__gte=hour_start,
                timestamp__lt=hour_end
            ).count()
            
            hourly_events.append({
                'hour': hour_start.strftime('%H:00'),
                'count': hourly_count
            })
        
        # Top users with most events
        top_users = list(events_qs.exclude(user__isnull=True).values(
            'user__username', 'user__email'
        ).annotate(
            event_count=Count('id')
        ).order_by('-event_count')[:10])
        
        # Recent critical events
        recent_critical = list(SystemEvent.objects.filter(
            severity=SystemEvent.SeverityLevels.CRITICAL
        ).order_by('-timestamp')[:5].values(
            'id', 'event_type', 'timestamp', 'user__username', 'details', 'resolved'
        ))
        
        # Unresolved events by severity
        unresolved_by_severity = list(SystemEvent.objects.filter(
            resolved=False
        ).values('severity').annotate(
            count=Count('id')
        ).order_by('-count'))
        
        # Convert data to JSON for JavaScript
        context.update({
            'events_by_type_json': json.dumps(events_by_type),
            'events_by_severity_json': json.dumps(events_by_severity),
            'daily_events_json': json.dumps(daily_events),
            'hourly_events_json': json.dumps(hourly_events),
            'top_users_json': json.dumps(top_users),
            'recent_critical_json': json.dumps(recent_critical, default=str),
            'unresolved_by_severity_json': json.dumps(unresolved_by_severity),
        })
        
        return context


class AnalyticsApiView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """API endpoint for real-time analytics data"""
    permission_required = 'system_events.view_systemevent'
    
    def get(self, request, *args, **kwargs):
        metric = request.GET.get('metric')
        days = int(request.GET.get('days', 7))
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        events_qs = SystemEvent.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        if metric == 'events_trend':
            # Get daily events for trend chart
            daily_data = []
            for i in range(days):
                day = start_date + timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                count = events_qs.filter(
                    timestamp__gte=day_start,
                    timestamp__lt=day_end
                ).count()
                
                daily_data.append({
                    'date': day.strftime('%Y-%m-%d'),
                    'count': count
                })
            
            return JsonResponse({'data': daily_data})
        
        elif metric == 'severity_distribution':
            severity_data = list(events_qs.values('severity').annotate(
                count=Count('id')
            ).order_by('-count'))
            
            return JsonResponse({'data': severity_data})
        
        elif metric == 'event_types':
            type_data = list(events_qs.values('event_type').annotate(
                count=Count('id')
            ).order_by('-count')[:10])
            
            return JsonResponse({'data': type_data})
        
        return JsonResponse({'error': 'Invalid metric'}, status=400)


class AttendanceAnalyticsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'analytics/attendance.html'
    permission_required = 'booking.view_computerbookingattendance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate date ranges
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Get computer booking attendance stats
        booking_attendance = ComputerBookingAttendance.objects.filter(
            booking__start_time__date__range=[start_date, end_date]
        ).aggregate(
            total=Count('id'),
            present=Count(Case(When(status='present', then=1), output_field=IntegerField())),
            late=Count(Case(When(status='late', then=1), output_field=IntegerField())),
            absent=Count(Case(When(status='absent', then=1), output_field=IntegerField())),
            excused=Count(Case(When(status='excused', then=1), output_field=IntegerField())),
        )
        
        # Get session attendance stats
        session_attendance = SessionAttendance.objects.filter(
            session__start_time__date__range=[start_date, end_date]
        ).aggregate(
            total=Count('id'),
            present=Count(Case(When(status='present', then=1), output_field=IntegerField())),
            late=Count(Case(When(status='late', then=1), output_field=IntegerField())),
            absent=Count(Case(When(status='absent', then=1), output_field=IntegerField())),
            excused=Count(Case(When(status='excused', then=1), output_field=IntegerField())),
        )
        
        context['booking_attendance'] = booking_attendance
        context['session_attendance'] = session_attendance
        
        # Calculate attendance rates
        if booking_attendance['total'] > 0:
            context['booking_attendance_rate'] = (booking_attendance['present'] + booking_attendance['late']) / booking_attendance['total'] * 100
        else:
            context['booking_attendance_rate'] = 0
            
        if session_attendance['total'] > 0:
            context['session_attendance_rate'] = (session_attendance['present'] + session_attendance['late']) / session_attendance['total'] * 100
        else:
            context['session_attendance_rate'] = 0
        
        return context


def is_admin(user):
    return hasattr(user, 'is_admin') and user.is_admin

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
    ).select_related('computer', 'student', 'attendance').order_by('start_time')
    
    # Get today's lab sessions
    today_sessions = LabSession.objects.filter(
        start_time__date=today,
        is_approved=True
    ).select_related('lab', 'lecturer').prefetch_related('attending_students').order_by('start_time')
    
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
    
    # Pre-calculate attendance counts for each session
    session_attendance = {}
    for session in today_sessions:
        present_count = SessionAttendance.objects.filter(
            session=session, 
            status='present'
        ).count()
        session_attendance[session.id] = present_count
    
    # If user is lab-specific admin, filter by their labs
    if request.user.is_admin and not request.user.is_super_admin:
        managed_labs = request.user.managed_labs.all()
        today_bookings = today_bookings.filter(computer__lab__in=managed_labs)
        today_sessions = today_sessions.filter(lab__in=managed_labs)
    
    context = {
        'today_bookings': today_bookings,
        'today_sessions': today_sessions,
        'booking_attendance': booking_attendance,
        'session_attendance': session_attendance,
        'today': today,
        'now': timezone.now()
    }
    
    return render(request, 'check_in_dashboard.html', context)