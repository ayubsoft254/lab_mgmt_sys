from django.db import models

# Create your models here.
class SystemEvent(models.Model):
    EVENT_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('registration', 'User Registration'),
        ('booking_created', 'Booking Created'),
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('session_created', 'Lab Session Created'),
        ('session_approved', 'Lab Session Approved'),
        ('session_rejected', 'Lab Session Rejected'),
        ('maintenance_request', 'Maintenance Request'),
        ('maintenance_resolved', 'Maintenance Resolved'),
        ('system_error', 'System Error'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='system_events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(null=True, blank=True)  # Store additional context as JSON
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    def __str__(self):
        if self.user:
            return f"{self.event_type} - {self.user.username} at {self.timestamp}"
        return f"{self.event_type} at {self.timestamp}"