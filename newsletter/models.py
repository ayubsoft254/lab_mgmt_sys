from django.db import models
import uuid
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.storage import default_storage
import csv


User = get_user_model()

# Create your models here.

class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    receive_updates = models.BooleanField(default=True, help_text="System updates and improvements")
    receive_lab_news = models.BooleanField(default=True, help_text="News about lab facilities and availability")
    receive_tips = models.BooleanField(default=False, help_text="Tips and best practices for using labs")
    receive_events = models.BooleanField(default=False, help_text="Lab workshops and special events")
    is_active = models.BooleanField(default=True)
    unsubscribe_token = models.CharField(max_length=255, unique=True)
    source = models.CharField(max_length=20, default='main', choices=(
        ('main', 'Main Newsletter Form'),
        ('footer', 'Footer Form'),
        ('popup', 'Popup Form'),
        ('import', 'CSV Import'),
        ('admin', 'Admin Added'),
        ('other', 'Other Source'),
    ))
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email
        
    class Meta:
        verbose_name = "Newsletter Subscription"
        verbose_name_plural = "Newsletter Subscriptions"
        ordering = ['-created_at']

class EmailTemplate(models.Model):
    """Reusable email templates for campaigns"""
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=200)
    html_content = models.TextField(help_text="HTML content for the email")
    text_content = models.TextField(help_text="Plain text version (for email clients that don't support HTML)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
        
    class Meta:
        ordering = ['name']

class EmailCampaign(models.Model):
    """Email campaign for sending to multiple users"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    RECIPIENT_CHOICES = (
        ('all_users', 'All System Users'),
        ('students', 'Student Users Only'),
        ('lecturers', 'Lecturers Only'),
        ('admins', 'Administrators Only'),
        ('subscribers', 'Newsletter Subscribers'),
        ('csv_upload', 'CSV Upload Recipients')
    )
    
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=200)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    custom_html_content = models.TextField(blank=True, help_text="Custom HTML content (if not using template)")
    custom_text_content = models.TextField(blank=True, help_text="Custom plain text content (if not using template)")
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_CHOICES, default='all_users')
    sender_email = models.EmailField(blank=True, help_text="Sender email address (if different from default)")
    csv_file = models.FileField(upload_to='email_campaigns/csv/', blank=True, null=True, help_text="CSV file with recipient data")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_email_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Campaign statistics
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name
    
    @property
    def html_content(self):
        """Get HTML content from template or custom content"""
        if self.template:
            return self.template.html_content
        return self.custom_html_content
    
    @property
    def text_content(self):
        """Get text content from template or custom content"""
        if self.template:
            return self.template.text_content
        return self.custom_text_content
    
    def get_recipients_queryset(self):
        """Get queryset of recipient users based on selected recipient type"""
        if self.recipient_type == 'all_users':
            return User.objects.filter(is_active=True)
        elif self.recipient_type == 'students':
            return User.objects.filter(is_active=True, is_student=True)
        elif self.recipient_type == 'lecturers':
            return User.objects.filter(is_active=True, is_lecturer=True)
        elif self.recipient_type == 'admins':
            return User.objects.filter(is_active=True, is_admin=True)
        elif self.recipient_type == 'subscribers':
            return User.objects.filter(email__in=NewsletterSubscription.objects.filter(
                is_active=True).values_list('email', flat=True))
        elif self.recipient_type == 'csv_upload':
            email_list = []
            if not self.csv_file:
                try:
                    with default_storage.open(self.csv_file.name, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            email = row.get('email', '').strip().lower()
                            if email:
                                email_list.append(email)
                except Exception as e:
                    # Optionally log error: logger.error(f"CSV processing error: {e}")
                    return User.objects.none()

        return User.objects.filter(email__in=email_list, is_active=True)
        return User.objects.filter(email__in=email_list, is_active=True)
        
            
            
        
    
    def get_csv_recipients(self):
        """Get CSV recipients for this campaign"""
        return self.csv_recipients.all()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Campaign'
        verbose_name_plural = 'Email Campaigns'

class EmailDelivery(models.Model):
    """Tracks individual email deliveries for a campaign"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
    )
    
    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name='deliveries')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_emails')
    email_address = models.EmailField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    tracking_id = models.UUIDField(default=uuid.uuid4, editable=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.email_address} - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name_plural = "Email deliveries"

class CsvRecipient(models.Model):
    """Store recipients from CSV uploads for campaigns"""
    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name='csv_recipients')
    email = models.EmailField()
    data = models.JSONField(default=dict, help_text="Additional data from CSV for placeholders")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.email} - {self.campaign.name}"
    
    class Meta:
        ordering = ['email']
        unique_together = ['campaign', 'email']