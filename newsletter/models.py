from django.db import models

# Create your models here.

class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    receive_updates = models.BooleanField(default=True)
    receive_lab_news = models.BooleanField(default=True)
    receive_tips = models.BooleanField(default=False)
    receive_events = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    source = models.CharField(max_length=20, default='main')  # 'main' or 'footer'
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.email
