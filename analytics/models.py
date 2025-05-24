from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Store additional data like 'request_time' here as JSON
    details = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.event_type} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"