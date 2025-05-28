from django import forms
from .models import AnonymousFeedback

class AnonymousFeedbackForm(forms.ModelForm):
    """Form for users to submit anonymous feedback"""
    
    class Meta:
        model = AnonymousFeedback
        fields = ['category', 'message', 'rating', 'page_url']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select rounded-lg border-gray-300 focus:border-ttu-green focus:ring focus:ring-ttu-light focus:ring-opacity-50'}),
            'message': forms.Textarea(attrs={'rows': 4, 'class': 'form-textarea rounded-lg border-gray-300 focus:border-ttu-green focus:ring focus:ring-ttu-light focus:ring-opacity-50', 'placeholder': 'Your feedback helps us improve. Feel free to share your thoughts...'}),
            'rating': forms.RadioSelect(attrs={'class': 'form-radio text-ttu-green focus:ring-ttu-green'}),
            'page_url': forms.HiddenInput(),
        }
        labels = {
            'category': 'Type of Feedback',
            'message': 'Your Feedback',
            'rating': 'Rate Your Experience (Optional)',
        }