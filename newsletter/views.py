from django.shortcuts import render, redirect
from django.contrib import messages
from .models import NewsletterSubscription
# Ensure utils.py exists in the same directory as this views.py file.
from .utils import send_welcome_email

# Create your views here.

def subscribe_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        name = request.POST.get('name', '')
        form_location = request.POST.get('form_location', 'unknown')
        email_types = request.POST.getlist('email_type')
        
        # If it's the footer form with minimal fields
        if form_location == 'footer':
            # Set default subscription preferences
            email_types = ['lab_news']
        
        # Check if email already exists
        existing_subscriber = NewsletterSubscription.objects.filter(email=email).first()
        
        if existing_subscriber:
            messages.info(request, "You're already subscribed to our newsletter!")
        else:
            # Create new subscription
            subscription = NewsletterSubscription(
                email=email,
                name=name,
                receive_updates='updates' in email_types,
                receive_lab_news='lab_news' in email_types,
                receive_tips='tips' in email_types,
                receive_events='events' in email_types,
            )
            subscription.save()
            
            # Send welcome email
            send_welcome_email(email, name)
            
            messages.success(request, "Thanks for subscribing to our newsletter!")
        
        # Redirect back to the landing page with a success message
        return redirect('home')
    
    return redirect('home')
