from django.shortcuts import render, redirect
from django.contrib import messages
from .models import NewsletterSubscription
# Ensure utils.py exists in the same directory as this views.py file.
from .utils import send_welcome_email
from django.http import HttpResponse
from django.utils import timezone

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

def track_email_open(request, tracking_id):
    """
    Track when an email is opened via a tracking pixel
    Returns a 1x1 transparent GIF
    """
    from .models import EmailDelivery
    
    try:
        # Find the delivery by tracking ID
        delivery = EmailDelivery.objects.get(tracking_id=tracking_id)
        
        # Only update if this is the first time it's opened
        if delivery.status != 'opened' and not delivery.opened_at:
            delivery.status = 'opened'
            delivery.opened_at = timezone.now()
            delivery.save()
            
            # Update campaign stats
            campaign = delivery.campaign
            campaign.open_count += 1
            campaign.save()
    except EmailDelivery.DoesNotExist:
        pass
        
    # Return a transparent 1x1 pixel GIF
    transparent_pixel = (
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
        b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
        b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    )
    
    return HttpResponse(transparent_pixel, content_type='image/gif')

def track_email_click(request, tracking_id, redirect_url):
    """
    Track when a link in an email is clicked and redirect to the target URL
    """
    from .models import EmailDelivery
    
    try:
        # Find the delivery by tracking ID
        delivery = EmailDelivery.objects.get(tracking_id=tracking_id)
        
        # Update status
        delivery.status = 'clicked'
        if not delivery.clicked_at:
            delivery.clicked_at = timezone.now()
        delivery.save()
        
        # Update campaign stats
        campaign = delivery.campaign
        campaign.click_count += 1
        campaign.save()
    except EmailDelivery.DoesNotExist:
        pass
    
    # Redirect to the target URL (with safety checks)
    if redirect_url.startswith('http://') or redirect_url.startswith('https://'):
        return redirect(redirect_url)
    else:
        # For safety, require protocol in the URL
        return redirect('/')

def unsubscribe(request, token):
    """
    Handle unsubscription requests from emails
    """
    from .utils import unsubscribe_user
    from .models import NewsletterSubscription
    
    try:
        subscription = NewsletterSubscription.objects.get(unsubscribe_token=token)
        subscription.is_active = False
        subscription.save()
        
        messages.success(request, "You have been successfully unsubscribed from our newsletter.")
    except NewsletterSubscription.DoesNotExist:
        messages.error(request, "Invalid unsubscription link.")
    
    return redirect('home')