from django.shortcuts import render, redirect
from django.contrib import messages
from .models import NewsletterSubscription
# Ensure utils.py exists in the same directory as this views.py file.
from .utils import send_welcome_email
from django.http import HttpResponse
from django.utils import timezone
import uuid  # Add this import

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
            try:
                # Generate a unique unsubscribe token
                unsubscribe_token = str(uuid.uuid4())
                
                # Create new subscription
                subscription = NewsletterSubscription(
                    email=email,
                    name=name,
                    receive_updates='updates' in email_types,
                    receive_lab_news='lab_news' in email_types,
                    receive_tips='tips' in email_types,
                    receive_events='events' in email_types,
                    unsubscribe_token=unsubscribe_token  # Set the token here
                )
                subscription.save()
                
                # Send welcome email
                send_welcome_email(email, name)
                
                messages.success(request, "Thanks for subscribing to our newsletter!")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        
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

@admin.site.admin_view
def send_bulk_email(request):
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        user_ids = request.session.get('selected_user_ids', [])
        
        users = User.objects.filter(id__in=user_ids)
        
        # Create a campaign
        campaign = EmailCampaign.objects.create(
            name=f"Ad hoc email: {subject}",
            subject=subject,
            custom_html_content=f"<div>{message}</div>",
            custom_text_content=message,
            recipient_type='custom',
            created_by=request.user,
            status='sending',
            started_at=timezone.now()
        )
        
        # Set campaign details
        campaign.total_recipients = users.count()
        campaign.save()
        
        # Create delivery records
        deliveries = []
        for user in users:
            deliveries.append(EmailDelivery(
                campaign=campaign,
                recipient=user,
                email_address=user.email,
                status='pending'
            ))
        
        # Bulk create delivery records
        EmailDelivery.objects.bulk_create(deliveries)
        
        # Process the campaign
        from .tasks import process_email_campaign
        process_email_campaign(campaign.id)
        
        messages.success(request, f"Email is being sent to {users.count()} users.")
        return redirect('admin:newsletter_emailcampaign_changelist')
    
    return render(request, 'admin/send_bulk_email.html', {
        'title': 'Send Email to Selected Users',
        'user_count': len(request.session.get('selected_user_ids', [])),
    })