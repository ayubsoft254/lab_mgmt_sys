from django.db import models
import uuid

# Create your models here.

class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    receive_updates = models.BooleanField(default=True, help_text="System updates and improvements")
    receive_lab_news = models.BooleanField(default=True, help_text="News about lab facilities and availability")
    receive_tips = models.BooleanField(default=False, help_text="Tips and best practices for using labs")
    receive_events = models.BooleanField(default=False, help_text="Lab workshops and special events")
    is_active = models.BooleanField(default=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
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
