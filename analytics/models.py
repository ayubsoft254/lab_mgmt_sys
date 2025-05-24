from django.db import models
from django.conf import settings
from django.utils import timezone

class SystemEventQuerySet(models.QuerySet):
    def with_related(self):
        """Prefetch related objects to optimize queries"""
        return self.select_related(
            'user',
            'resolved_by',
            'booking',
            'session'
        )
    
    def unresolved(self):
        """Get unresolved events"""
        return self.filter(resolved=False)
    
    def critical_events(self):
        """Get critical severity events"""
        return self.filter(severity=4)
    
    def for_dashboard(self, days=7):
        """Get events optimized for dashboard display"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return (
            self.filter(timestamp__gte=cutoff_date)
            .with_related()
            .order_by('-severity', '-timestamp')
        )


class SystemEventManager(models.Manager):
    def get_queryset(self):
        return SystemEventQuerySet(self.model, using=self._db)
    
    def log_event(self, event_type, user=None, details=None, ip_address=None, 
                 booking=None, session=None, severity=1, **kwargs):
        """Create a new system event log entry with additional context"""
        event_data = {
            'event_type': event_type,
            'user': user,
            'ip_address': ip_address,
            'booking': booking,
            'session': session,
            'severity': severity,
            'details': details or {}
        }
        event_data['details'].update(kwargs)
        return self.create(**event_data)
    
    def get_events_for_user(self, user, days=None):
        """Get events for a specific user, optionally filtered by time"""
        queryset = self.filter(user=user)
        if days:
            cutoff_date = timezone.now() - timezone.timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=cutoff_date)
        return queryset
    
    def get_security_events(self, days=30):
        """Get security-related events"""
        security_types = [
            SystemEvent.EventTypes.LOGIN,
            SystemEvent.EventTypes.LOGOUT,
            SystemEvent.EventTypes.SECURITY_ALERT,
            SystemEvent.EventTypes.PASSWORD_CHANGE,
            SystemEvent.EventTypes.PERMISSION_CHANGE
        ]
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(
            event_type__in=security_types,
            timestamp__gte=cutoff_date
        )


class SystemEvent(models.Model):
    class EventTypes(models.TextChoices):
        LOGIN = 'login', 'User Login'
        LOGOUT = 'logout', 'User Logout'
        REGISTRATION = 'registration', 'User Registration'
        BOOKING_CREATED = 'booking_created', 'Booking Created'
        BOOKING_APPROVED = 'booking_approved', 'Booking Approved'
        BOOKING_REJECTED = 'booking_rejected', 'Booking Rejected'
        BOOKING_CANCELLED = 'booking_cancelled', 'Booking Cancelled'
        SESSION_CREATED = 'session_created', 'Lab Session Created'
        SESSION_APPROVED = 'session_approved', 'Lab Session Approved'
        SESSION_REJECTED = 'session_rejected', 'Lab Session Rejected'
        MAINTENANCE_REQUEST = 'maintenance_request', 'Maintenance Request'
        MAINTENANCE_RESOLVED = 'maintenance_resolved', 'Maintenance Resolved'
        SYSTEM_ERROR = 'system_error', 'System Error'
        SECURITY_ALERT = 'security_alert', 'Security Alert'
        PASSWORD_CHANGE = 'password_change', 'Password Changed'
        PERMISSION_CHANGE = 'permission_change', 'Permission Changed'
    
    class SeverityLevels(models.IntegerChoices):
        LOW = 1, 'Low'
        MEDIUM = 2, 'Medium'
        HIGH = 3, 'High'
        CRITICAL = 4, 'Critical'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='system_events'
    )
    event_type = models.CharField(max_length=50, choices=EventTypes.choices)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    severity = models.PositiveSmallIntegerField(
        choices=SeverityLevels.choices,
        default=SeverityLevels.LOW,
        db_index=True
    )
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_events'
    )
    booking = models.ForeignKey(
        'booking.ComputerBooking', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='system_events'
    )
    session = models.ForeignKey(
        'booking.LabSession', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='system_events'
    )
    
    objects = SystemEventManager()
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['severity', 'resolved']),
            models.Index(fields=['resolved']),
        ]
        verbose_name = 'System Event'
        verbose_name_plural = 'System Events'
    
    def __str__(self):
        if self.user:
            return f"{self.get_event_type_display()} - {self.user.username} at {self.timestamp}"
        return f"{self.get_event_type_display()} at {self.timestamp}"
    
    def mark_as_resolved(self, resolved_by):
        """Mark this event as resolved"""
        self.resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.save(update_fields=['resolved', 'resolved_at', 'resolved_by'])
    
    def get_event_icon(self):
        """Get appropriate icon for the event type"""
        icons = {
            self.EventTypes.LOGIN: 'fa-sign-in-alt',
            self.EventTypes.LOGOUT: 'fa-sign-out-alt',
            self.EventTypes.SECURITY_ALERT: 'fa-shield-alt',
            self.EventTypes.REGISTRATION: 'fa-user-plus',
            self.EventTypes.BOOKING_CREATED: 'fa-calendar-plus',
            self.EventTypes.BOOKING_APPROVED: 'fa-calendar-check',
            self.EventTypes.BOOKING_REJECTED: 'fa-calendar-times',
            self.EventTypes.SYSTEM_ERROR: 'fa-exclamation-triangle',
            self.EventTypes.MAINTENANCE_REQUEST: 'fa-tools',
            self.EventTypes.PASSWORD_CHANGE: 'fa-key',
            self.EventTypes.PERMISSION_CHANGE: 'fa-user-cog',
        }
        return icons.get(self.event_type, 'fa-info-circle')
    
    def is_security_event(self):
        """Check if this is a security-related event"""
        return self.event_type in [
            self.EventTypes.LOGIN,
            self.EventTypes.LOGOUT,
            self.EventTypes.SECURITY_ALERT,
            self.EventTypes.PASSWORD_CHANGE,
            self.EventTypes.PERMISSION_CHANGE
        ]