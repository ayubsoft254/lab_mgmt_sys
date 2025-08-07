from django import forms
from .models import EmailCampaign, EmailTemplate
import csv
import io
from django.core.exceptions import ValidationError
from django.conf import settings

def get_email_choices():
    """Get available email choices from settings"""
    choices = []
    
    # Add default email if available
    if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER:
        choices.append((settings.EMAIL_HOST_USER, "Host Email ({})".format(settings.EMAIL_HOST_USER)))
    
    # Add admissions email if available
    if hasattr(settings, 'EMAIL_HOST_USER_ADMISSIONS') and settings.EMAIL_HOST_USER_ADMISSIONS:
        choices.append((settings.EMAIL_HOST_USER_ADMISSIONS, "Admissions Email ({})".format(settings.EMAIL_HOST_USER_ADMISSIONS)))
    
    # Add a custom option
    choices.append(('custom', 'Custom Email (enter below)'))
    
    return choices

class CsvEmailCampaignForm(forms.ModelForm):
    csv_file = forms.FileField(
        required=True,
        help_text="CSV file with columns: email, name, reg, course, hostel, room"
    )
    sender_email_choice = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=True,
        label="Sender Email",
        help_text="Select sender email from available options"
    )
    custom_sender_email = forms.EmailField(
        required=False,
        label="Custom Sender Email",
        help_text="Only required if 'Custom Email' is selected above"
    )
    
    class Meta:
        model = EmailCampaign
        fields = ['name', 'subject', 'template', 'custom_html_content', 'custom_text_content', 'csv_file', 'scheduled_time']
        widgets = {
            'custom_html_content': forms.Textarea(attrs={'rows': 10}),
            'custom_text_content': forms.Textarea(attrs={'rows': 8}),
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sender_email_choice'].choices = get_email_choices()
        
        # Set initial value if editing existing campaign
        if self.instance and self.instance.pk and self.instance.sender_email:
            sender_email = self.instance.sender_email
            # Check if it matches one of our predefined emails
            choice_values = [choice[0] for choice in get_email_choices()]
            if sender_email in choice_values:
                self.fields['sender_email_choice'].initial = sender_email
            else:
                self.fields['sender_email_choice'].initial = 'custom'
                self.fields['custom_sender_email'].initial = sender_email
    
    def clean(self):
        cleaned_data = super().clean()
        sender_choice = cleaned_data.get('sender_email_choice')
        custom_email = cleaned_data.get('custom_sender_email')
        
        if sender_choice == 'custom':
            if not custom_email:
                raise ValidationError("Custom sender email is required when 'Custom Email' is selected.")
            # Set the sender_email for the model
            cleaned_data['sender_email'] = custom_email
        else:
            # Use the selected predefined email
            cleaned_data['sender_email'] = sender_choice
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set the sender_email from our cleaned data
        instance.sender_email = self.cleaned_data.get('sender_email')
        if commit:
            instance.save()
        return instance
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            raise ValidationError("File must be a CSV file.")
        
        # Read and validate CSV
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('utf-8')
            csv_file.seek(0)  # Reset file pointer
            
            reader = csv.DictReader(io.StringIO(content))
            headers = reader.fieldnames
            
            # Check for required columns
            required_columns = ['email', 'name', 'reg', 'course', 'hostel', 'room']
            if not headers:
                raise ValidationError("CSV file appears to be empty or invalid.")
            
            missing_columns = [col for col in required_columns if col not in headers]
            if missing_columns:
                raise ValidationError("CSV file is missing required columns: {}. Required columns are: {}".format(
                    ', '.join(missing_columns), ', '.join(required_columns)))
            
            # Validate at least one row exists
            rows = list(reader)
            if not rows:
                raise ValidationError("CSV file cannot be empty.")
            
            # Validate data in each row
            for i, row in enumerate(rows, 1):
                # Check email
                email = row.get('email', '').strip()
                if not email:
                    raise ValidationError("Row {}: Email address is required.".format(i))
                
                # Basic email validation
                if '@' not in email or '.' not in email.split('@')[1]:
                    raise ValidationError("Row {}: Invalid email address '{}'.".format(i, email))
                
                # Check name
                name = row.get('name', '').strip()
                if not name:
                    raise ValidationError("Row {}: Name is required.".format(i))
                
                # Check registration number
                reg = row.get('reg', '').strip()
                if not reg:
                    raise ValidationError("Row {}: Registration number is required.".format(i))
                
                # Check course
                course = row.get('course', '').strip()
                if not course:
                    raise ValidationError("Row {}: Course is required.".format(i))
                
                # Check hostel
                hostel = row.get('hostel', '').strip()
                if not hostel:
                    raise ValidationError("Row {}: Hostel is required.".format(i))
                
                # Check room
                room = row.get('room', '').strip()
                if not room:
                    raise ValidationError("Row {}: Room number is required.".format(i))
            
        except UnicodeDecodeError:
            raise ValidationError("CSV file must be UTF-8 encoded.")
        except Exception as e:
            raise ValidationError("Error reading CSV file: {}".format(str(e)))
        
        return csv_file

class SenderEmailForm(forms.Form):
    sender_email_choice = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=True,
        label="Sender Email",
        help_text="Select sender email from available options"
    )
    custom_sender_email = forms.EmailField(
        required=False,
        label="Custom Sender Email",
        help_text="Only required if 'Custom Email' is selected above",
        widget=forms.EmailInput(attrs={'placeholder': 'sender@example.com'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sender_email_choice'].choices = get_email_choices()
    
    def clean(self):
        cleaned_data = super().clean()
        sender_choice = cleaned_data.get('sender_email_choice')
        custom_email = cleaned_data.get('custom_sender_email')
        
        if sender_choice == 'custom':
            if not custom_email:
                raise ValidationError("Custom sender email is required when 'Custom Email' is selected.")
            cleaned_data['final_sender_email'] = custom_email
        else:
            cleaned_data['final_sender_email'] = sender_choice
        
        return cleaned_data

class EmailCampaignAdminForm(forms.ModelForm):
    sender_email_choice = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=True,
        label="Sender Email",
        help_text="Select sender email from available options"
    )
    custom_sender_email = forms.EmailField(
        required=False,
        label="Custom Sender Email",
        help_text="Only required if 'Custom Email' is selected above"
    )
    scheduled_time = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(date_attrs={'type': 'date'}, time_attrs={'type': 'time'}),
        required=False
    )
    
    class Meta:
        model = EmailCampaign
        fields = [
            'name', 'subject', 'template', 'custom_html_content', 'custom_text_content',
            'recipient_type', 'csv_file', 'scheduled_time'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sender_email_choice'].choices = get_email_choices()
        
        # Set initial value if editing existing campaign
        if self.instance and self.instance.pk and self.instance.sender_email:
            sender_email = self.instance.sender_email
            # Check if it matches one of our predefined emails
            choice_values = [choice[0] for choice in get_email_choices()]
            if sender_email in choice_values:
                self.fields['sender_email_choice'].initial = sender_email
            else:
                self.fields['sender_email_choice'].initial = 'custom'
                self.fields['custom_sender_email'].initial = sender_email
    
    def clean(self):
        cleaned_data = super().clean()
        sender_choice = cleaned_data.get('sender_email_choice')
        custom_email = cleaned_data.get('custom_sender_email')
        
        if sender_choice == 'custom':
            if not custom_email:
                raise ValidationError("Custom sender email is required when 'Custom Email' is selected.")
            cleaned_data['sender_email'] = custom_email
        else:
            cleaned_data['sender_email'] = sender_choice
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.sender_email = self.cleaned_data.get('sender_email')
        if commit:
            instance.save()
        return instance