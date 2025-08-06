from django import forms
from .models import EmailCampaign
import csv
import io
from django.core.exceptions import ValidationError

class CsvEmailCampaignForm(forms.ModelForm):
    csv_file = forms.FileField(
        required=True,
        help_text="CSV file with email addresses and additional data. First column must be 'email'."
    )
    sender_email = forms.EmailField(
        required=False,
        help_text="Leave blank to use default sender email"
    )
    
    class Meta:
        model = EmailCampaign
        fields = ['name', 'subject', 'template', 'custom_html_content', 'custom_text_content', 'sender_email', 'csv_file', 'scheduled_time']
        widgets = {
            'custom_html_content': forms.Textarea(attrs={'rows': 10}),
            'custom_text_content': forms.Textarea(attrs={'rows': 8}),
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
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
            
            if not headers or 'email' not in headers:
                raise ValidationError("CSV file must have an 'email' column.")
            
            # Validate at least one row exists
            rows = list(reader)
            if not rows:
                raise ValidationError("CSV file cannot be empty.")
            
            # Validate email addresses
            for i, row in enumerate(rows, 1):
                email = row.get('email', '').strip()
                if not email:
                    raise ValidationError(f"Row {i}: Email address is required.")
                
                # Basic email validation
                if '@' not in email or '.' not in email.split('@')[1]:
                    raise ValidationError(f"Row {i}: Invalid email address '{email}'.")
            
        except UnicodeDecodeError:
            raise ValidationError("CSV file must be UTF-8 encoded.")
        except Exception as e:
            raise ValidationError(f"Error reading CSV file: {str(e)}")
        
        return csv_file

class SenderEmailForm(forms.Form):
    sender_email = forms.EmailField(
        required=False,
        help_text="Leave blank to use default sender email",
        widget=forms.EmailInput(attrs={'placeholder': 'sender@example.com'})
    )