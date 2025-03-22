from django import forms
from .models import ComputerBooking, LabSession, Lab, Computer, User
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),        
    )
    
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data['role']
        
        if role == 'student':
            user.is_student = True
        elif role == 'lecturer':
            user.is_lecturer = True
        elif role == 'admin':
            user.is_admin = True
            user.is_staff = True
        
        if commit:
            user.save()
        return user

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