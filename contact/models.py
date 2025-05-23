from django.db import models

class ContactSubmission(models.Model):
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