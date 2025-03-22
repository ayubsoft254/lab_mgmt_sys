from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid

class User(AbstractUser):
    is_student = models.BooleanField(default=False)
    is_lecturer = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username

class Lab(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    capacity = models.IntegerField(help_text="Total number of computers in the lab")
    
    def __str__(self):
        return self.name

class Computer(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name='computers')
    computer_number = models.IntegerField()
    specs = models.TextField(blank=True, help_text="Computer specifications")
    status = models.CharField(max_length=20, choices=[
        ('available', 'Available'),
        ('maintenance', 'Under Maintenance'),
        ('reserved', 'Reserved')
    ], default='available')
    
    class Meta:
        unique_together = ('lab', 'computer_number')
    
    def __str__(self):
        return f"{self.lab.name} - Computer #{self.computer_number}"

class LabSession(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name='sessions')
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booked_sessions')
    title = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        # Check if end time is after start time
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
            
        # Check if lab is available for the requested time slot
        conflicting_sessions = LabSession.objects.filter(
            lab=self.lab,
            is_approved=True,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(id=self.id)
        
        if conflicting_sessions.exists():
            raise ValidationError('Lab is already booked for this time slot')
        
        # Check if there are less than 10 computer bookings during this time
        booked_computers_count = ComputerBooking.objects.filter(
            computer__lab=self.lab,
            is_approved=True,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).count()
        
        if booked_computers_count > 10 and not self.is_approved:
            raise ValidationError('Cannot book lab session when more than 10 computers are already booked')
    
    def save(self, *args, **kwargs):
        self.clean()
        super(LabSession, self).save(*args, **kwargs)
        
        # If the lab has 5 or more booked computers and the session is approved,
        # cancel existing computer bookings
        if self.is_approved:
            lab_computers_count = self.lab.computers.count()
            if lab_computers_count >= 5:
                conflicting_bookings = ComputerBooking.objects.filter(
                    computer__lab=self.lab,
                    is_approved=True,
                    start_time__lt=self.end_time,
                    end_time__gt=self.start_time
                )
                
                # Create notifications for affected students
                for booking in conflicting_bookings:
                    Notification.objects.create(
                        user=booking.student,
                        message=f"Your booking for {booking.computer} has been cancelled due to a lab session scheduled by a lecturer. Please rebook.",
                        notification_type='booking_cancelled'
                    )
                
                # Cancel the conflicting bookings
                conflicting_bookings.update(is_cancelled=True)
    
    def __str__(self):
        return f"{self.lab.name} Session: {self.title} ({self.start_time.strftime('%Y-%m-%d %H:%M')} - {self.end_time.strftime('%H:%M')})"

class ComputerBooking(models.Model):
    computer = models.ForeignKey(Computer, on_delete=models.CASCADE, related_name='bookings')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='computer_bookings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    booking_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_approved = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        # Check if end time is after start time
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
        
        # Check if computer is available for the requested time slot
        if not self.is_cancelled:
            conflicting_bookings = ComputerBooking.objects.filter(
                computer=self.computer,
                is_approved=True,
                is_cancelled=False,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exclude(id=self.id)
            
            if conflicting_bookings.exists():
                raise ValidationError('Computer is already booked for this time slot')
                
            # Check if there's a lab session during this time
            conflicting_sessions = LabSession.objects.filter(
                lab=self.computer.lab,
                is_approved=True,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            )
            
            if conflicting_sessions.exists():
                raise ValidationError('Lab is reserved for a session during this time slot')
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.clean()
        super(ComputerBooking, self).save(*args, **kwargs)
        
        # Notify admin about new booking
        if is_new:
            admin_users = User.objects.filter(is_admin=True)
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    message=f"New computer booking: {self.computer} by {self.student.username}",
                    notification_type='new_booking'
                )
    
    def __str__(self):
        return f"Booking {self.booking_code}: {self.computer} - {self.start_time.strftime('%Y-%m-%d %H:%M')} to {self.end_time.strftime('%H:%M')}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('new_booking', 'New Booking'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('session_booked', 'Session Booked'),
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected')
    ])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.notification_type}"
