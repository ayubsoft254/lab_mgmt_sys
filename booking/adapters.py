from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        
        # Set user role based on form data
        role = form.cleaned_data.get('role')
        if role == 'student':
            user.is_student = True
        elif role == 'lecturer':
            user.is_lecturer = True
        elif role == 'admin':
            user.is_admin = True
            
        if commit:
            user.save()
        return user

    def clean_email(self, email):
        email = super().clean_email(email)
        # Add any custom email validation here
        return email
