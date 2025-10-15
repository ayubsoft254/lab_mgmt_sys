from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

User = get_user_model()

class Inquiry(models.Model):
    """Model for user inquiries to administrators"""
    CATEGORY_CHOICES = [
        ('general', 'General Inquiry'),
        ('technical', 'Technical Support'),
        ('booking', 'Booking Assistance'),
        ('account', 'Account/Profile'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    # User information
    name = models.CharField(max_length=100)
    email = models.EmailField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inquiries')
    
    # Inquiry details
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_response = models.TextField(blank=True, null=True)
    admin_responder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inquiry_responses')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Inquiries'
    
    def __str__(self):
        return f"{self.subject} - {self.name} ({self.get_status_display()})"
    
    def mark_resolved(self, responder):
        """Mark inquiry as resolved"""
        self.status = 'resolved'
        self.admin_responder = responder
        self.resolved_at = timezone.now()
        self.save()
    
    def get_admin_url(self):
        """Get the admin URL for this inquiry"""
        return reverse('admin:contact_inquiry_change', args=[self.id])


class Feedback(models.Model):
    """Model for user feedback"""
    CATEGORY_CHOICES = [
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('ui', 'UI/UX Improvement'),
        ('performance', 'Performance Issue'),
        ('other', 'Other'),
    ]
    
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]
    
    # User information
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    
    # Feedback details
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    title = models.CharField(max_length=200)
    message = models.TextField()
    rating = models.IntegerField(choices=RATING_CHOICES, default=3)
    
    # Admin notes
    admin_notes = models.TextField(blank=True, null=True)
    is_actionable = models.BooleanField(default=False, help_text="Mark if this feedback requires action")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_rating_display()}"


class ContactSubmission(models.Model):
    """Legacy model for backward compatibility"""
    SUBJECT_CHOICES = [
        ('General Inquiry', 'General Inquiry'),
        ('Technical Support', 'Technical Support'),
        ('Booking Assistance', 'Booking Assistance'),
        ('Feedback', 'Feedback'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=100, choices=SUBJECT_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.subject} ({self.created_at.strftime('%Y-%m-%d')})"