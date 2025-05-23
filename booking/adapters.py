from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

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
            # Note: Lab assignments would typically be handled by a super admin later
        elif role == 'super_admin':
            user.is_admin = True
            user.is_super_admin = True
            
        if commit:
            user.save()
        return user

    def clean_email(self, email):
        email = super().clean_email(email).lower().strip()  # Normalize email
        request = self.request  # Access the request object from the adapter
        form_data = request.POST if request else {}

        # Get the selected role (from form submission)
        role = form_data.get('role')

        # Skip validation if role isn't provided (e.g., admin updates)
        if not role:
            return email

        # Define allowed domains per role
        allowed_domains = {
            'student': '@students.ttu.ac.ke',
            'lecturer': '@ttu.ac.ke',
        }

        required_domain = allowed_domains.get(role)

        # If role exists but email doesn't match the required domain
        if required_domain and not email.endswith(required_domain):
            raise ValidationError(
                _(f"Invalid email domain for {role}s. Must use {required_domain}")
            )

        return email