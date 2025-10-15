from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
from dateutil.parser import parse
from django.db.models import Q
from datetime import timedelta

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
    # Adding attending students relation
    attending_students = models.ManyToManyField(User, related_name='attending_sessions', blank=True)
    description = models.TextField(blank=True, null=True)
    
    # Add cancelled field
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)
    
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
        
        # If new lab session is created, notify relevant admins (no duplicates)
        if is_new:
            # Get all unique admins (lab-specific and super admins)
            lab_admins = User.objects.filter(is_admin=True, managed_labs=self.lab)
            super_admins = User.objects.filter(is_super_admin=True)
            all_admins = set(list(lab_admins) + list(super_admins))
            for admin in all_admins:
                Notification.objects.create(
                    user=admin,
                    message=f"New lab session: {self.title} in {self.lab.name} by {self.lecturer.username}",
                    notification_type='session_booked',
                    lab_session=self
                )
    
    def __str__(self):
        return f"{self.title} - {self.lab.name} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"

    def cancel_session(self, reason=''):
        """Cancel a lab session if it's approved and not already cancelled"""
        if not self.is_approved or self.is_cancelled:
            return False
            
        # Only allow cancellation if start time is in the future (at least 2 hours ahead)
        if self.start_time <= (timezone.now() + timedelta(hours=2)):
            return False
            
        self.is_cancelled = True
        self.cancellation_reason = reason
        self.save(update_fields=['is_cancelled', 'cancellation_reason'])
        
        # Notify admins about cancellation
        lab_admins = User.objects.filter(
            is_admin=True, 
            managed_labs=self.lab
        )
        
        # Create notifications for lab-specific admins
        for admin in lab_admins:
            Notification.objects.create(
                user=admin,
                message=f"Lab session '{self.title}' in {self.lab.name} has been cancelled by {self.lecturer.username}. Reason: {reason or 'No reason provided'}",
                notification_type='session_cancelled',
                lab_session=self
            )
            
        # Notify attending students
        for student in self.attending_students.all():
            Notification.objects.create(
                user=student,
                message=f"Lab session '{self.title}' scheduled for {self.start_time.strftime('%Y-%m-%d %H:%M')} has been cancelled.",
                notification_type='session_cancelled',
                lab_session=self
            )
            
        return True

    def record_student_attendance(self, student, status, admin_user, check_in_time=None, check_out_time=None, notes=''):
        """Record attendance for a student in this session"""
        if check_in_time is None:
            check_in_time = timezone.now()
            
        # Check if student is in attending_students, add if not
        if student not in self.attending_students.all():
            self.attending_students.add(student)
            
        attendance, created = SessionAttendance.objects.update_or_create(
            session=self,
            student=student,
            defaults={
                'status': status,
                'check_in_time': check_in_time,
                'check_out_time': check_out_time,
                'notes': notes,
                'checked_by': admin_user
            }
        )
        
        # Create notification for the student
        Notification.objects.create(
            user=student,
            message=f"Your attendance for '{self.title}' session has been marked as {attendance.get_status_display()}",
            notification_type='attendance_marked',
            lab_session=self
        )
        
        return attendance

    def bulk_attendance_check(self, students_data, admin_user):
        """Record attendance for multiple students at once
        
        students_data: list of dicts with keys 'student_id', 'status', and optionally 'notes'
        """
        results = []
        for data in students_data:
            try:
                student = User.objects.get(id=data['student_id'])
                attendance = self.record_student_attendance(
                    student=student,
                    status=data['status'],
                    admin_user=admin_user,
                    notes=data.get('notes', '')
                )
                results.append({
                    'student': student.username,
                    'status': 'success',
                    'attendance': attendance.get_status_display()
                })
            except User.DoesNotExist:
                results.append({
                    'student_id': data['student_id'],
                    'status': 'error',
                    'message': 'Student not found'
                })
        return results

class ComputerBooking(models.Model):
    computer = models.ForeignKey(Computer, on_delete=models.CASCADE, related_name='bookings')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='computer_bookings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    booking_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_approved = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    purpose = models.TextField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True)
    
    # Add these fields
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)
    extension_requested = models.BooleanField(default=False)
    extension_requested_at = models.DateTimeField(null=True, blank=True)
    extension_approved = models.BooleanField(default=False)
    extension_approved_at = models.DateTimeField(null=True, blank=True)
    
    def clean(self):
        # Check if end time is after start time
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
        
        # Check if computer is available for the requested time slot
        # Only check for conflicts if the booking is not cancelled
        if not self.is_cancelled:
            # Only check conflicts with approved bookings when this booking is being approved
            # OR when creating a new booking
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
                is_cancelled=False,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            )
            
            if conflicting_sessions.exists():
                raise ValidationError('Lab is reserved for a session during this time slot')
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.clean()
        
        # Set timestamps if status changed
        if not is_new:
            old_booking = ComputerBooking.objects.get(pk=self.pk)
            if not old_booking.is_approved and self.is_approved:
                self.approved_at = timezone.now()
            if not old_booking.is_cancelled and self.is_cancelled:
                self.cancelled_at = timezone.now()
            if not old_booking.extension_requested and self.extension_requested:
                self.extension_requested_at = timezone.now()
            if not old_booking.extension_approved and self.extension_approved:
                self.extension_approved_at = timezone.now()
                
        super(ComputerBooking, self).save(*args, **kwargs)
        
        # Notify relevant admins about new booking (no duplicates)
        if is_new:
            lab_admins = User.objects.filter(is_admin=True, managed_labs=self.computer.lab)
            super_admins = User.objects.filter(is_super_admin=True)
            all_admins = set(list(lab_admins) + list(super_admins))
            for admin in all_admins:
                Notification.objects.create(
                    user=admin,
                    message=f"New computer booking: {self.computer} by {self.student.username}",
                    notification_type='new_booking',
                    booking=self
                )
    
    def __str__(self):
        return f"Booking {self.booking_code}: {self.computer} - {self.start_time.strftime('%Y-%m-%d %H:%M')} to {self.end_time.strftime('%H:%M')}"
    
    def can_be_extended(self):
        """Check if booking can be extended by 30 minutes"""
        if self.is_cancelled or not self.is_approved:
            return False
            
        # Calculate potential extended end time
        extended_end_time = self.end_time + timedelta(minutes=30)
        
        # Check if there's another booking for this computer right after
        next_bookings = ComputerBooking.objects.filter(
            computer=self.computer,
            is_approved=True,
            is_cancelled=False,
            start_time__gt=self.end_time,
            start_time__lt=extended_end_time
        )
        
        # Check if there's a lab session during the extended time
        lab_sessions = LabSession.objects.filter(
            lab=self.computer.lab,
            is_approved=True,
            start_time__lt=extended_end_time,
            end_time__gt=self.end_time
        )
        
        return not (next_bookings.exists() or lab_sessions.exists())
    
    def extend_booking(self):
        """Extend the booking by 30 minutes if possible"""
        if not self.can_be_extended():
            return False
            
        self.end_time = self.end_time + timedelta(minutes=30)
        self.extension_requested = True
        self.extension_approved = True
        self.extension_requested_at = timezone.now()
        self.extension_approved_at = timezone.now()
        self.save(update_fields=['end_time', 'extension_requested', 'extension_approved', 
                                 'extension_requested_at', 'extension_approved_at'])
        
        # Create notification for the user
        Notification.objects.create(
            user=self.student,
            message=f"Your booking for {self.computer} has been extended by 30 minutes until {self.end_time.strftime('%H:%M')}",
            notification_type='booking_extended',
            booking=self
        )
        return True

    def mark_attendance(self, status, admin_user, check_in_time=None, check_out_time=None, notes=''):
        """Mark attendance for this booking"""
        if check_in_time is None:
            check_in_time = timezone.now()
            
        attendance, created = ComputerBookingAttendance.objects.update_or_create(
            booking=self,
            defaults={
                'status': status,
                'check_in_time': check_in_time,
                'check_out_time': check_out_time,
                'notes': notes,
                'checked_by': admin_user
            }
        )
        
        # Create notification for the student
        Notification.objects.create(
            user=self.student,
            message=f"Your attendance for booking at {self.computer} has been marked as {attendance.get_status_display()}",
            notification_type='attendance_marked',
            booking=self
        )
        
        return attendance

    def cancel_booking(self, reason=''):
        """Cancel a booking if it's approved and not already cancelled"""
        if not self.is_approved or self.is_cancelled:
            return False
            
        # Only allow cancellation if start time is in the future (at least 30 minutes ahead)
        if self.start_time <= (timezone.now() + timedelta(minutes=30)):
            return False
            
        self.is_cancelled = True
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save(update_fields=['is_cancelled', 'cancelled_at', 'cancellation_reason'])
        
        # Notify admins about cancellation
        lab_admins = User.objects.filter(
            is_admin=True, 
            managed_labs=self.computer.lab
        )
        
        # Create notifications for lab-specific admins
        for admin in lab_admins:
            Notification.objects.create(
                user=admin,
                message=f"Booking {self.booking_code} for {self.computer} has been cancelled by {self.student.username}. Reason: {reason or 'No reason provided'}",
                notification_type='booking_cancelled',
                booking=self
            )
            
        # Create notification for the student
        Notification.objects.create(
            user=self.student,
            message=f"Your booking for {self.computer} on {self.start_time.strftime('%Y-%m-%d %H:%M')} has been cancelled successfully",
            notification_type='booking_cancelled',
            booking=self
        )
        
        return True
    
    @property
    def attendance(self):
        """Get the attendance record for this booking if it exists"""
        try:
            return self.computerbookingattendance
        except ComputerBookingAttendance.DoesNotExist:
            return None

class RecurringSession(models.Model):
    RECURRENCE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ]
    
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name='recurring_sessions')
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
            ).exclude(pk=self.pk if self.pk else None)
            
            if conflicting_sessions.exists() or conflicting_recurring_sessions.exists():
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
        ('recurring_session_rejected', 'Recurring Session Rejected'),
        ('booking_ending', 'Booking Ending Soon'),
        ('booking_extended', 'Booking Extended'),
        ('extension_unavailable', 'Extension Unavailable'),
        ('checkin_reminder', 'Check-in Reminder'),
        ('attendance_marked', 'Attendance Marked'),
        ('attendance_updated', 'Attendance Updated'),
        ('session_cancelled', 'Session Cancelled'),
    ])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional references to different entities
    booking = models.ForeignKey(ComputerBooking, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    lab_session = models.ForeignKey(LabSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    recurring_session = models.ForeignKey(RecurringSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.notification_type}"    

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
    session = models.ForeignKey(LabSession, on_delete=models.CASCADE, related_name='student_ratings', null=True, blank=True)
    booking = models.ForeignKey(ComputerBooking, on_delete=models.CASCADE, related_name='student_ratings', null=True, blank=True)
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

class Attendance(models.Model):
    """Base abstract model for attendance tracking"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='absent')
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    checked_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='%(class)s_checks'
    )
    
    class Meta:
        abstract = True

class ComputerBookingAttendance(Attendance):
    """Track attendance for individual computer bookings"""
    booking = models.OneToOneField(
        ComputerBooking, 
        on_delete=models.CASCADE, 
        related_name='attendance'
    )
    
    def __str__(self):
        return f"Attendance for {self.booking} - {self.get_status_display()}"
    
class SessionAttendance(Attendance):
    """Track attendance for lab sessions with multiple students"""
    session = models.ForeignKey(
        LabSession, 
        on_delete=models.CASCADE, 
        related_name='attendance_records'
    )
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='session_attendance'
    )
    
    class Meta:
        unique_together = ('session', 'student')
    
    def __str__(self):
        return f"Attendance for {self.student} in {self.session} - {self.get_status_display()}"