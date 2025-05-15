from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Computer, LabSession, RecurringSession, ComputerBooking

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

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        role = cleaned_data.get('role')

        # Check if role is selected and email is provided
        if role == 'student':
            if email and not email.endswith('@students.ttu.ac.ke'):
                self.add_error('email', 'Students must use @students.ttu.ac.ke email.')
        elif role == 'lecturer':
            if email and not email.endswith('@ttu.ac.ke'):
                self.add_error('email', 'Lecturers must use @ttu.ac.ke email.')
        
        # Ensure email is present if role is selected
        if role and not email:
            self.add_error('email', 'Email is required for the selected role.')
        
        return cleaned_data  # Correctly return cleaned_data

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        
        # Assign role-specific attributes
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