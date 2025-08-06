from celery import shared_task
import logging
import time
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task
def process_email_campaign(campaign_id):
    """Process an email campaign by sending emails to all recipients"""
    from .models import EmailCampaign, EmailDelivery, CsvRecipient
    
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        
        if campaign.status != 'sending':
            logger.warning(f"Campaign {campaign.id} is not in 'sending' state. Current state: {campaign.status}")
            return
        
        logger.info(f"Processing campaign '{campaign.name}' with {campaign.total_recipients} recipients")
        
        # Determine sender email
        sender_email = campaign.sender_email if campaign.sender_email else settings.DEFAULT_FROM_EMAIL
        
        if campaign.recipient_type == 'csv_upload':
            # Process CSV recipients
            csv_recipients = campaign.csv_recipients.all()
            
            for csv_recipient in csv_recipients:
                try:
                    # Create context with CSV data
                    context = {
                        'email': csv_recipient.email,
                        **csv_recipient.data,  # Add all CSV columns as context variables
                        'tracking_pixel': f"{settings.BASE_URL}/track/open/csv_{csv_recipient.id}/",
                    }
                    
                    # Create email with both HTML and plain text
                    msg = EmailMultiAlternatives(
                        subject=Template(campaign.subject).render(Context(context)),
                        body=Template(campaign.text_content).render(Context(context)),
                        from_email=sender_email,
                        to=[csv_recipient.email]
                    )
                    
                    # Add HTML content with tracking pixel
                    html_content = Template(campaign.html_content).render(Context(context))
                    tracking_pixel = f'<img src="{context["tracking_pixel"]}" width="1" height="1" alt="">'
                    html_with_tracking = html_content + tracking_pixel
                    
                    msg.attach_alternative(html_with_tracking, "text/html")
                    
                    # Send email
                    msg.send()
                    
                    # Update campaign stats
                    campaign.sent_count += 1
                    campaign.save()
                    
                    # Small delay to avoid overloading email server
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error sending to {csv_recipient.email}: {str(e)}")
        else:
            # Process regular deliveries
            deliveries = EmailDelivery.objects.filter(campaign=campaign, status='pending')
            
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
                        'email': email,
                        'tracking_pixel': f"{settings.BASE_URL}/track/open/{delivery.tracking_id}/",
                    }
                    
                    # Create email with both HTML and plain text
                    msg = EmailMultiAlternatives(
                        subject=Template(campaign.subject).render(Context(context)),
                        body=Template(campaign.text_content).render(Context(context)),
                        from_email=sender_email,
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