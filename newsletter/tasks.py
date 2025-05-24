from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
import logging
import time

logger = logging.getLogger(__name__)

def process_email_campaign(campaign_id):
    """Process an email campaign by sending emails to all recipients"""
    from .models import EmailCampaign, EmailDelivery
    
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        
        if campaign.status != 'sending':
            logger.warning(f"Campaign {campaign.id} is not in 'sending' state. Current state: {campaign.status}")
            return
        
        logger.info(f"Processing campaign '{campaign.name}' with {campaign.total_recipients} recipients")
        
        # Get all pending deliveries
        deliveries = EmailDelivery.objects.filter(campaign=campaign, status='pending')
        
        # Process each delivery
        for delivery in deliveries:
            try:
                # Get recipient info
                recipient = delivery.recipient
                email = delivery.email_address
                
                # Skip if no email
                if not email:
                    delivery.status = 'failed'
                    delivery.error_message = 'No email address for recipient'
                    delivery.save()
                    continue
                
                # Personalize email content
                context = {
                    'user': recipient,
                    'first_name': recipient.first_name or '',
                    'last_name': recipient.last_name or '',
                    'tracking_pixel': f"{settings.BASE_URL}/newsletter/track/open/{delivery.tracking_id}/",
                }
                
                # Create email with both HTML and plain text
                msg = EmailMultiAlternatives(
                    subject=campaign.subject,
                    body=Template(campaign.text_content).render(Context(context)),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email]
                )
                
                # Add HTML content with tracking pixel
                html_content = Template(campaign.html_content).render(Context(context))
                tracking_pixel = f'<img src="{context["tracking_pixel"]}" width="1" height="1" alt="">'
                html_with_tracking = html_content + tracking_pixel
                
                msg.attach_alternative(html_with_tracking, "text/html")
                
                # Send email
                msg.send()
                
                # Update delivery status
                delivery.status = 'sent'
                delivery.sent_at = timezone.now()
                delivery.save()
                
                # Update campaign stats
                campaign.sent_count += 1
                campaign.save()
                
                # Small delay to avoid overloading email server
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error sending to {delivery.email_address}: {str(e)}")
                delivery.status = 'failed'
                delivery.error_message = str(e)
                delivery.save()
        
        # Update campaign status
        campaign.status = 'completed'
        campaign.completed_at = timezone.now()
        campaign.save()
        
        logger.info(f"Campaign '{campaign.name}' completed. Sent: {campaign.sent_count}")
        
    except EmailCampaign.DoesNotExist:
        logger.error(f"Campaign with ID {campaign_id} not found")
    except Exception as e:
        logger.error(f"Error processing campaign {campaign_id}: {str(e)}")
        
        try:
            campaign = EmailCampaign.objects.get(id=campaign_id)
            campaign.status = 'failed'
            campaign.save()
        except:
            pass