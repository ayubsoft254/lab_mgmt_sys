from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('lecturer', 'Lecturer'),
        ('student', 'Student'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)

class LabResource(models.Model):
    LAB_CHOICES = (
        ('lab1', 'Lab 1'),
        ('lab2', 'Lab 2'),
    )
    name = models.CharField(max_length=100)
    description = models.TextField()
    resource_type = models.CharField(max_length=50)  # computer/space
    is_available = models.BooleanField(default=True)
    lab = models.CharField(max_length=10, choices=LAB_CHOICES)
    computer_number = models.IntegerField(unique=True)  # Unique number for each computer in the lab

    def __str__(self):
        return f"{self.lab} - Computer {self.computer_number}"

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(LabResource, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, default='pending')

    def clean(self):
        # Check if the user is a student and already has a booking
        if self.user.user_type == 'student' and Booking.objects.filter(user=self.user, status='confirmed').exists():
            raise ValidationError("Students can only book one computer at a time.")

        # Check if the user is a lecturer and trying to book the entire lab
        if self.user.user_type == 'lecturer':
            # Ensure the lecturer is booking all computers in the lab
            lab_computers = LabResource.objects.filter(lab=self.resource.lab)
            if not Booking.objects.filter(resource__in=lab_computers, user=self.user, status='confirmed').count() == lab_computers.count():
                raise ValidationError("Lecturers must book the entire lab.")

        # Check if the resource is available
        if not self.resource.is_available:
            raise ValidationError("The selected resource is not available.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def send_notification(self):
        from notifications.signals import notify
        notify.send(
            self.user,
            recipient=self.user,
            verb='booked',
            action_object=self,
            description=f'Your booking for {self.resource.name} is confirmed'
        )

class Ticket(models.Model):
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    def __str__(self):
        return self.title