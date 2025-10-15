from django import forms
from .models import Inquiry, Feedback


class InquiryForm(forms.ModelForm):
    """Form for submitting inquiries to administrators"""
    
    class Meta:
        model = Inquiry
        fields = ['name', 'email', 'category', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name',
                'required': 'required',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com',
                'required': 'required',
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief subject of your inquiry',
                'required': 'required',
                'maxlength': '200',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Please provide details about your inquiry. The more information you provide, the better we can assist you.',
                'rows': 6,
                'required': 'required',
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Please enter your name.")
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long.")
        return name
    
    def clean_subject(self):
        subject = self.cleaned_data.get('subject', '').strip()
        if not subject:
            raise forms.ValidationError("Please enter a subject.")
        if len(subject) < 5:
            raise forms.ValidationError("Subject must be at least 5 characters long.")
        return subject
    
    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if not message:
            raise forms.ValidationError("Please enter your message.")
        if len(message) < 10:
            raise forms.ValidationError("Message must be at least 10 characters long.")
        return message


class FeedbackForm(forms.ModelForm):
    """Form for submitting feedback"""
    
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'category', 'title', 'message', 'rating']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name (optional)',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com (optional)',
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required',
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief title for your feedback',
                'required': 'required',
                'maxlength': '200',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tell us what you think. Your feedback is valuable to us.',
                'rows': 6,
                'required': 'required',
            }),
            'rating': forms.RadioSelect(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # Pre-fill name and email if user is logged in
        if user and user.is_authenticated:
            self.fields['name'].initial = user.get_full_name() or user.username
            self.fields['email'].initial = user.email
            # Make these fields read-only for logged-in users
            self.fields['name'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['readonly'] = True
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Please enter a title for your feedback.")
        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long.")
        return title
    
    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if not message:
            raise forms.ValidationError("Please enter your feedback.")
        if len(message) < 10:
            raise forms.ValidationError("Feedback must be at least 10 characters long.")
        return message


class AdminInquiryResponseForm(forms.ModelForm):
    """Form for admin to respond to inquiries"""
    
    class Meta:
        model = Inquiry
        fields = ['status', 'admin_response']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
            'admin_response': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Type your response here...',
                'rows': 6,
            }),
        }
    
    def clean_admin_response(self):
        """Ensure response is provided if status is being set to resolved"""
        admin_response = self.cleaned_data.get('admin_response', '').strip()
        status = self.cleaned_data.get('status')
        
        if status == 'resolved' and not admin_response:
            raise forms.ValidationError("Please provide a response before marking as resolved.")
        
        return admin_response
