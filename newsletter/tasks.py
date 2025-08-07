from celery import shared_task
import logging
import time
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)

@shared_task
def process_email_campaign(campaign_id):
    """Process an email campaign by sending emails to all recipients"""
    from .models import EmailCampaign, EmailDelivery, CsvRecipient
    
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        
        if campaign.status != 'sending':
            logger.warning("Campaign {} is not in 'sending' state. Current state: {}".format(
                campaign.id, campaign.status))
            return
        
        logger.info("Processing campaign '{}' with {} recipients".format(
            campaign.name, campaign.total_recipients))
        
        # Determine sender email
        sender_email = campaign.sender_email if campaign.sender_email else settings.DEFAULT_FROM_EMAIL
        
        if campaign.recipient_type == 'csv_upload':
            # Process CSV recipients directly in this task
            csv_recipients = campaign.csv_recipients.all()
            
            for csv_recipient in csv_recipients:
                try:
                    # Create context with CSV data
                    context = {
                        'email': csv_recipient.email,
                        **csv_recipient.data,  # Add all CSV columns as context variables
                        'tracking_pixel': "{}/newsletter/track/open/csv_{}/".format(
                            getattr(settings, 'BASE_URL', 'http://localhost:8000'),
                            csv_recipient.id
                        ),
                    }
                    
                    # Send the email
                    success = send_campaign_email(campaign, csv_recipient.email, context, sender_email)
                    
                    if success:
                        # Update campaign stats atomically
                        EmailCampaign.objects.filter(id=campaign_id).update(
                            sent_count=models.F('sent_count') + 1
                        )
                        logger.debug("Email sent successfully to {}".format(csv_recipient.email))
                    else:
                        logger.error("Failed to send email to {}".format(csv_recipient.email))
                    
                    # Small delay to avoid overloading email server
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error("Error sending to {}: {}".format(csv_recipient.email, str(e)))
            
            # Update campaign status
            campaign.status = 'completed'
            campaign.completed_at = timezone.now()
            campaign.save()
            
            logger.info("CSV campaign '{}' completed. Sent: {}".format(campaign.name, campaign.sent_count))
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
                        'first_name': getattr(recipient, 'first_name', '') or '',
                        'last_name': getattr(recipient, 'last_name', '') or '',
                        'email': email,
                        'tracking_pixel': "{}/newsletter/track/open/{}/".format(
                            getattr(settings, 'BASE_URL', 'http://localhost:8000'),
                            delivery.tracking_id
                        ),
                    }
                    
                    # Send the email
                    success = send_campaign_email(campaign, email, context, sender_email)
                    
                    if success:
                        # Update delivery status
                        delivery.status = 'sent'
                        delivery.sent_at = timezone.now()
                        delivery.save()
                        
                        # Update campaign stats atomically
                        EmailCampaign.objects.filter(id=campaign_id).update(
                            sent_count=models.F('sent_count') + 1
                        )
                    else:
                        delivery.status = 'failed'
                        delivery.error_message = 'Failed to send email'
                        delivery.save()
                    
                    # Small delay to avoid overloading email server
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error("Error sending to {}: {}".format(delivery.email_address, str(e)))
                    delivery.status = 'failed'
                    delivery.error_message = str(e)
                    delivery.save()
            
            # Update campaign status
            campaign.status = 'completed'
            campaign.completed_at = timezone.now()
            campaign.save()
            
            logger.info("Campaign '{}' completed. Sent: {}".format(campaign.name, campaign.sent_count))
        
    except EmailCampaign.DoesNotExist:
        logger.error("Campaign with ID {} not found".format(campaign_id))
    except Exception as e:
        logger.error("Error processing campaign {}: {}".format(campaign_id, str(e)))
        
        try:
            campaign = EmailCampaign.objects.get(id=campaign_id)
            campaign.status = 'failed'
            campaign.save()
        except:
            pass

@shared_task
def process_csv_campaign_batch(campaign_id, batch_size=50):
    """Process CSV campaign in batches to avoid memory issues (alternative approach)"""
    from .models import EmailCampaign, CsvRecipient
    
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        
        logger.info("Processing CSV campaign '{}' in batches of {}".format(
            campaign.name, batch_size))
        
        # Determine sender email
        sender_email = campaign.sender_email if campaign.sender_email else settings.DEFAULT_FROM_EMAIL
        
        # Get total count
        total_recipients = campaign.csv_recipients.count()
        
        # Process in batches
        for offset in range(0, total_recipients, batch_size):
            batch_recipients = campaign.csv_recipients.all()[offset:offset + batch_size]
            
            for csv_recipient in batch_recipients:
                try:
                    # Create context with CSV data
                    context = {
                        'email': csv_recipient.email,
                        **csv_recipient.data,
                        'tracking_pixel': "{}/newsletter/track/open/csv_{}/".format(
                            getattr(settings, 'BASE_URL', 'http://localhost:8000'),
                            csv_recipient.id
                        ),
                    }
                    
                    # Send the email
                    success = send_campaign_email(campaign, csv_recipient.email, context, sender_email)
                    
                    if success:
                        # Update campaign stats atomically
                        EmailCampaign.objects.filter(id=campaign_id).update(
                            sent_count=models.F('sent_count') + 1
                        )
                        logger.debug("Email sent successfully to {}".format(csv_recipient.email))
                    else:
                        logger.error("Failed to send email to {}".format(csv_recipient.email))
                    
                    # Small delay to avoid overloading email server
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error("Error sending to {}: {}".format(csv_recipient.email, str(e)))
            
            logger.info("Processed batch {}-{} of {}".format(
                offset + 1, min(offset + batch_size, total_recipients), total_recipients))
        
        # Update campaign status
        campaign.status = 'completed'
        campaign.completed_at = timezone.now()
        campaign.save()
        
        logger.info("CSV campaign '{}' completed. Total sent: {}".format(
            campaign.name, campaign.sent_count))
        
    except Exception as e:
        logger.error("Error processing CSV campaign in batches {}: {}".format(campaign_id, str(e)))
        try:
            campaign = EmailCampaign.objects.get(id=campaign_id)
            campaign.status = 'failed'
            campaign.save()
        except:
            pass

def send_campaign_email(campaign, recipient_email, context, sender_email):
    """Helper function to send a campaign email"""
    try:
        # Render subject and content with context
        subject = Template(campaign.subject).render(Context(context))
        text_content = Template(campaign.text_content or '').render(Context(context))
        html_content = Template(campaign.html_content or '').render(Context(context))
        
        # Create email message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=sender_email,
            to=[recipient_email]
        )
        
        # Add HTML content with tracking pixel if available
        if html_content:
            tracking_pixel = context.get('tracking_pixel', '')
            if tracking_pixel:
                tracking_img = '<img src="{}" width="1" height="1" alt="" style="display:none;">'.format(tracking_pixel)
                html_with_tracking = html_content + tracking_img
            else:
                html_with_tracking = html_content
            
            msg.attach_alternative(html_with_tracking, "text/html")
        
        # Send email
        msg.send()
        logger.info("Email sent successfully to {}".format(recipient_email))
        return True
        
    except Exception as e:
        logger.error("Error sending email to {}: {}".format(recipient_email, str(e)))
        return False

# Keep the old tasks for backward compatibility but make them work
@shared_task
def process_csv_campaign(campaign_id):
    """Legacy task - delegates to main process_email_campaign"""
    return process_email_campaign.delay(campaign_id)

@shared_task
def send_single_csv_email(campaign_id, csv_recipient_id):
    """Send email to a single CSV recipient"""
    from .models import EmailCampaign, CsvRecipient
    
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        csv_recipient = CsvRecipient.objects.get(id=csv_recipient_id)
        
        # Determine sender email
        sender_email = campaign.sender_email if campaign.sender_email else settings.DEFAULT_FROM_EMAIL
        
        # Create context with CSV data
        context = {
            'email': csv_recipient.email,
            **csv_recipient.data,
            'tracking_pixel': "{}/newsletter/track/open/csv_{}/".format(
                getattr(settings, 'BASE_URL', 'http://localhost:8000'),
                csv_recipient.id
            ),
        }
        
        # Send the email
        success = send_campaign_email(campaign, csv_recipient.email, context, sender_email)
        
        if success:
            # Update campaign stats atomically
            EmailCampaign.objects.filter(id=campaign_id).update(
                sent_count=models.F('sent_count') + 1
            )
            logger.info("Email sent to {}".format(csv_recipient.email))
            return True
        else:
            logger.error("Failed to send email to {}".format(csv_recipient.email))
            return False
            
    except Exception as e:
        logger.error("Error in send_single_csv_email: {}".format(str(e)))
        return False