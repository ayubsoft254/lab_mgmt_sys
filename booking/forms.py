from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Computer, LabSession, RecurringSession

User = get_user_model()

# Computer Booking Form
class ComputerBookingForm(forms.ModelForm):
    class Meta:
        model = Computer
        fields = ['status', 'lab']

# Lab Session Form
class LabSessionForm(forms.ModelForm):
    class Meta:
        model = LabSession
        fields = ['lab', 'start_time', 'end_time']

# Recurring Session Form
class RecurringSessionForm(forms.ModelForm):
    class Meta:
        model = RecurringSession
        fields = ['lab', 'start_date', 'end_date', 'recurrence_type', 'start_time', 'end_time']

# Custom User Creation Form
class CustomUserCreationForm(forms.ModelForm):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
        ('admin', 'Admin'),
    ]
    
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def clean_email(self):
        email = self.cleaned_data.get('email')
        role = self.cleaned_data.get('role')

        if role == 'student' and not email.endswith('@students.ttu.ac.ke'):
            raise ValidationError("Use your student Email Address")
        elif role in ['lecturer', 'admin'] and not email.endswith('@ttu.ac.ke'):
            raise ValidationError("Use Staff Email Address")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])

        role = self.cleaned_data['role']
        if role == 'student':
            user.is_student = True
        elif role == 'lecturer':
            user.is_lecturer = True
        elif role == 'admin':
            user.is_admin = True

        if commit:
            user.save()
        return user