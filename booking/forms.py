from django import forms
from django.core.exceptions import ValidationError
import re
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Computer, LabSession, RecurringSession, ComputerBooking, StudentRating

# Constants for domain validation
STUDENT_EMAIL_DOMAIN = 'students.ttu.ac.ke'
LECTURER_EMAIL_DOMAIN = 'ttu.ac.ke'

class ComputerBookingForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    
    class Meta:
        model = ComputerBooking
        fields = ['computer', 'date', 'start_time', 'end_time']
    
    def __init__(self, *args, **kwargs):
        self.lab_id = kwargs.pop('lab_id', None)
        super(ComputerBookingForm, self).__init__(*args, **kwargs)
        
        if self.lab_id:
            self.fields['computer'].queryset = Computer.objects.filter(
                lab_id=self.lab_id, 
                status='available'
            )
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if date and start_time and end_time:
            # Combine date and time fields
            start_datetime = timezone.make_aware(
                timezone.datetime.combine(date, start_time)
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(date, end_time)
            )
            
            # Ensure start time is in the future
            if start_datetime < timezone.now():
                self.add_error('start_time', 'Booking must be for a future time')
            
            # Ensure end time is after start time
            if end_datetime <= start_datetime:
                self.add_error('end_time', 'End time must be after start time')
            
            cleaned_data['start_time'] = start_datetime
            cleaned_data['end_time'] = end_datetime
        
        return cleaned_data

class LabSessionForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    
    class Meta:
        model = LabSession
        fields = ['lab', 'title', 'date', 'start_time', 'end_time']
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if date and start_time and end_time:
            # Combine date and time fields
            start_datetime = timezone.make_aware(
                timezone.datetime.combine(date, start_time)
            )
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(date, end_time)
            )
            
            # Ensure start time is in the future
            if start_datetime < timezone.now():
                self.add_error('start_time', 'Session must be scheduled for a future time')
            
            # Ensure end time is after start time
            if end_datetime <= start_datetime:
                self.add_error('end_time', 'End time must be after start time')
            
            cleaned_data['start_time'] = start_datetime
            cleaned_data['end_time'] = end_datetime
        
        return cleaned_data
    
class RecurringSessionForm(forms.ModelForm):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    
    class Meta:
        model = RecurringSession
        fields = ['lab', 'title', 'start_date', 'end_date', 'start_time', 'end_time', 'recurrence_type']
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Validate dates and times
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', 'End date must be after start date')
        
        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', 'End time must be after start time')
        
        # Check if start date is in the past
        if start_date and start_date < timezone.now().date():
            self.add_error('start_date', 'Start date cannot be in the past')
            
        # Check for reasonable date range (e.g., not scheduling too far in advance)
        if start_date and end_date and (end_date - start_date).days > 365:
            self.add_error('end_date', 'Recurring sessions cannot be scheduled more than a year in advance')
        
        return cleaned_data


User = get_user_model()

class CustomUserCreationForm(forms.ModelForm):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
    ]
    
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = User
        fields = ('username', 'email')
        labels = {'email': 'Email (Required)'}
        help_texts = {'email': ''}

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()

        if not email:
            raise ValidationError('Email is required for registration.')

        # Check uniqueness - do case-insensitive comparison
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already registered.")

        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")

        return password2

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email', '').lower().strip()
        role = cleaned_data.get('role')

        # Enforce role selection
        if not role:
            self.add_error('role', 'Role selection is required.')
            return cleaned_data

        # Enforce email presence
        if not email:
            self.add_error('email', 'Email is required for registration.')
            return cleaned_data

        # Domain patterns
        domain_patterns = {
            'student': f'^[a-zA-Z0-9._%+-]+@{STUDENT_EMAIL_DOMAIN}$',
            'lecturer': f'^[a-zA-Z0-9._%+-]+@{LECTURER_EMAIL_DOMAIN}$'
        }

        pattern = domain_patterns.get(role)
        if pattern and not re.match(pattern, email):
            # Custom friendly error message
            example_email = (
                f"someone@{STUDENT_EMAIL_DOMAIN}" if role == "student" else f"someone@{LECTURER_EMAIL_DOMAIN}"
            )
            self.add_error(
                'email',
                f'Invalid email for {role}. Use your institutional email like: {example_email}'
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])

        # Assign role flags (your model must have these)
        role = self.cleaned_data['role']
        user.is_student = (role == 'student')
        user.is_lecturer = (role == 'lecturer')

        if commit:
            user.save()

        return user       
    
    # ===== Allauth Compatibility Methods =====
    def custom_signup(self, request, user):
        """Optional: For additional user setup."""
        pass

    def try_save(self, request):
        """
        Required by allauth to return (user, None).
        """
        user = self.save()
        return (user, None)
    
    @property
    def by_passkey(self):        
        return False

class CustomSignupForm(CustomUserCreationForm):
    salutation = forms.ChoiceField(
        choices=User.SALUTATION_CHOICES, 
        label='Salutation', 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    first_name = forms.CharField(max_length=30, label='First Name')
    last_name = forms.CharField(max_length=30, label='Last Name')
    course = forms.CharField(max_length=100, label='Course/Program', required=False)
    school = forms.ChoiceField(choices=User.SCHOOL_CHOICES, label='School')
    
    is_student = forms.BooleanField(required=False, label='Register as Student')
    is_lecturer = forms.BooleanField(required=False, label='Register as Lecturer')
    
    def clean(self):
        cleaned_data = super().clean()
        is_student = cleaned_data.get('is_student')
        is_lecturer = cleaned_data.get('is_lecturer')
        
        # Ensure at least one role is selected
        if not is_student and not is_lecturer:
            raise forms.ValidationError("Please select at least one role: Student or Lecturer")
            
        # Lecturer shouldn't need to specify a course
        if is_lecturer and not is_student and cleaned_data.get('course'):
            cleaned_data['course'] = None
            
        return cleaned_data
    
    def save(self, request):
        user = super().save(request)
        user.salutation = self.cleaned_data['salutation']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.course = self.cleaned_data['course']
        user.school = self.cleaned_data['school']
        user.is_student = self.cleaned_data['is_student']
        user.is_lecturer = self.cleaned_data['is_lecturer']
        user.save()
        return user

class StudentRatingForm(forms.ModelForm):
    class Meta:
        model = StudentRating
        fields = ['score', 'comment']
        widgets = {
            'score': forms.RadioSelect(),
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional comment about the student\'s behavior'}),
        }