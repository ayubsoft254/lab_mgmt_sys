from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
from dateutil.parser import parse
from django.db.models import Q

class User(AbstractUser):
    SCHOOL_CHOICES = [
        ('SSI', 'School of Science and Informatics'),
        ('SBAESS', 'School of Business Administration and Economic Social Sciences'),
        ('SME', 'School of Mining and Engineering'),
        ('SoE', 'School of Education'),
        ('SAEES', 'School of Agriculture, Environment and Earth Sciences'),
    ]
    
    SALUTATION_CHOICES = [
        ('Mr.', 'Mr.'),
        ('Mrs.', 'Mrs.'),
        ('Ms.', 'Ms.'),
        ('Dr.', 'Dr.'),
        ('Prof.', 'Prof.'),
        ('Eng.', 'Eng.'),
        ('Hon.', 'Hon.'),
        ('', 'None')
    ]
    
    is_student = models.BooleanField(default=False)
    is_lecturer = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_super_admin = models.BooleanField(default=False)  # New field for super admins
    
    # Additional fields
    salutation = models.CharField(max_length=10, choices=SALUTATION_CHOICES, blank=True, default='')
    school = models.CharField(max_length=6, choices=SCHOOL_CHOICES, blank=True, null=True)
    course = models.CharField(max_length=100, blank=True, null=True)
    managed_labs = models.ManyToManyField('Lab', blank=True, related_name='lab_admins')  # Labs managed by this admin
    
    # Add average rating field with a default of 5
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_ratings = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        full_name = ""
        if self.salutation:
            full_name += f"{self.salutation} "
        
        if self.first_name and self.last_name:
            full_name += f"{self.first_name} {self.last_name}"
            return f"{full_name} ({self.username})"
        
        return self.username
    
    def get_full_name(self):
        """
        Return the full name with salutation if available
        """
        if self.salutation and self.first_name and self.last_name:
            return f"{self.salutation} {self.first_name} {self.last_name}"
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def update_average_rating(self):
        """Update the user's average rating based on all ratings received"""
        ratings = self.ratings_received.all()
        if ratings.exists():
            total_score = sum(rating.score for rating in ratings)
            self.average_rating = round(total_score / ratings.count(), 2)
            self.total_ratings = ratings.count()
        else:
            self.average_rating = 5.00  # Default rating for new users
            self.total_ratings = 0
        self.save(update_fields=['average_rating', 'total_ratings'])
    
    class Meta:
        ordering = ['username']

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
        is_new = self.pk is None
        self.clean()
        super(LabSession, self).save(*args, **kwargs)
        
        # If new lab session is created, notify relevant admins
        if is_new:
            # Get admins specifically assigned to this lab
            lab_admins = User.objects.filter(
                is_admin=True, 
                managed_labs=self.lab
            )
            
            # Get super admins
            super_admins = User.objects.filter(is_super_admin=True)
            
            # Create notifications for lab-specific admins
            for admin in lab_admins:
                Notification.objects.create(
                    user=admin,
                    message=f"New lab session: {self.title} in {self.lab.name} by {self.lecturer.username}",
                    notification_type='session_booked',
                    lab_session=self
                )
            
            # Create notifications for super admins (if they're not already notified as lab admins)
            for admin in super_admins.exclude(id__in=lab_admins.values_list('id', flat=True)):
                Notification.objects.create(
                    user=admin,
                    message=f"New lab session: {self.title} in {self.lab.name} by {self.lecturer.username}",
                    notification_type='session_booked',
                    lab_session=self
                )
        
        # Rest of existing logic...

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
        
        # Notify relevant admins about new booking
        if is_new:
            # Get admins specifically assigned to this lab
            lab_admins = User.objects.filter(
                is_admin=True, 
                managed_labs=self.computer.lab
            )
            
            # Get super admins
            super_admins = User.objects.filter(is_super_admin=True)
            
            # Create notifications for lab-specific admins
            for admin in lab_admins:
                Notification.objects.create(
                    user=admin,
                    message=f"New computer booking: {self.computer} by {self.student.username}",
                    notification_type='new_booking',
                    booking=self
                )
            
            # Create notifications for super admins (if they're not already notified as lab admins)
            for admin in super_admins.exclude(id__in=lab_admins.values_list('id', flat=True)):
                Notification.objects.create(
                    user=admin,
                    message=f"New computer booking: {self.computer} by {self.student.username}",
                    notification_type='new_booking',
                    booking=self
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
        ('booking_rejected', 'Booking Rejected'),
        ('recurring_session_created', 'Recurring Session Created'),
        ('recurring_session_approved', 'Recurring Session Approved'),
        ('recurring_session_rejected', 'Recurring Session Rejected')
    ])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional references to different entities
    booking = models.ForeignKey('ComputerBooking', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    lab_session = models.ForeignKey('LabSession', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    recurring_session = models.ForeignKey('RecurringSession', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.notification_type}"    

class RecurringSession(models.Model):
    RECURRENCE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ]
    
    lab = models.ForeignKey('Lab', on_delete=models.CASCADE, related_name='recurring_sessions')
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_sessions')
    title = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    start_date = models.DateField()
    end_date = models.DateField()
    recurrence_type = models.CharField(max_length=10, choices=RECURRENCE_CHOICES)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        # Validate time and date ranges
        if self.end_date < self.start_date:
            raise ValidationError('End date must be after start date')
        
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
        
        # Check for conflicts with existing lab sessions and recurring sessions
        conflicts = self.check_session_conflicts()
        if conflicts:
            raise ValidationError(f'Conflicts exist with existing sessions: {conflicts}')
    
    def check_session_conflicts(self):
        conflicts = []
        
        # Get all occurrence dates
        occurrence_dates = list(rrule(
            freq={'daily': DAILY, 'weekly': WEEKLY, 'monthly': MONTHLY}[self.recurrence_type],
            dtstart=parse(f"{self.start_date} {self.start_time}"),
            until=parse(f"{self.end_date} {self.end_time}")
        ))
        
        for occurrence in occurrence_dates:
            # Check conflicts with existing lab sessions
            conflicting_sessions = LabSession.objects.filter(
                Q(lab=self.lab) &
                Q(start_time__lt=occurrence + timezone.timedelta(hours=self.end_time.hour, minutes=self.end_time.minute)) &
                Q(end_time__gt=occurrence + timezone.timedelta(hours=self.start_time.hour, minutes=self.start_time.minute)) &
                Q(is_approved=True)
            )
            
            # Check conflicts with other recurring sessions
            conflicting_recurring_sessions = RecurringSession.objects.filter(
                Q(lab=self.lab) &
                Q(start_date__lte=occurrence.date()) &
                Q(end_date__gte=occurrence.date()) &
                Q(is_approved=True)
            )
            
            if conflicting_sessions or conflicting_recurring_sessions:
                conflicts.append(occurrence.strftime('%Y-%m-%d %H:%M'))
        
        return conflicts
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        # If the recurring session is approved, create individual lab sessions
        if self.is_approved:
            occurrence_dates = list(rrule(
                freq={'daily': DAILY, 'weekly': WEEKLY, 'monthly': MONTHLY}[self.recurrence_type],
                dtstart=parse(f"{self.start_date} {self.start_time}"),
                until=parse(f"{self.end_date} {self.end_time}")
            ))
            
            for occurrence in occurrence_dates:
                start_datetime = timezone.make_aware(occurrence)
                end_datetime = timezone.make_aware(occurrence + timezone.timedelta(
                    hours=self.end_time.hour, 
                    minutes=self.end_time.minute
                ))
                
                LabSession.objects.create(
                    lab=self.lab,
                    lecturer=self.lecturer,
                    title=self.title,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    is_approved=True
                )
    
    def __str__(self):
        return f"{self.title} - {self.recurrence_type.capitalize()} from {self.start_date} to {self.end_date}"

class LabAdministrator(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lab_admin_roles')
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name='admin_assignments')
    date_assigned = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('admin', 'lab')
        verbose_name = 'Lab Administrator'
        verbose_name_plural = 'Lab Administrators'
    
    def __str__(self):
        return f"{self.admin.username} - {self.lab.name} Admin"

class StudentRating(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_received')
    rated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_given')
    score = models.PositiveSmallIntegerField(choices=[
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ])
    session = models.ForeignKey('LabSession', on_delete=models.CASCADE, related_name='student_ratings', null=True, blank=True)
    booking = models.ForeignKey('ComputerBooking', on_delete=models.CASCADE, related_name='student_ratings', null=True, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [
            ('student', 'rated_by', 'session'),
            ('student', 'rated_by', 'booking'),
        ]
        # Ensure either session or booking is provided, but not both
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(session__isnull=False, booking__isnull=True) | 
                    models.Q(session__isnull=True, booking__isnull=False)
                ),
                name='rating_has_either_session_or_booking'
            )
        ]
    
    def __str__(self):
        return f"{self.student.username} - {self.score} stars by {self.rated_by.username}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the student's average rating
        self.student.update_average_rating()