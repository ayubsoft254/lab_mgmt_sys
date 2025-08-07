from celery import shared_task
import logging
import time
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.db import models
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_email_campaign(self, campaign_id):
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
            total_recipients = csv_recipients.count()
            
            for index, csv_recipient in enumerate(csv_recipients, 1):
                try:
                    # Validate email before sending
                    validate_email(csv_recipient.email)
                    
                    # Create context with CSV data
                    context = {
                        'email': csv_recipient.email,
                        **csv_recipient.data,
                        'tracking_pixel': f"{settings.BASE_URL}/newsletter/track/open/csv_{csv_recipient.id}/",
                    }
                    
                    # Send the email
                    success = send_campaign_email(campaign, csv_recipient.email, context, sender_email)
                    
                    if success:
                        # Update campaign stats atomically
                        EmailCampaign.objects.filter(id=campaign_id).update(
                            sent_count=models.F('sent_count') + 1
                        )
                        logger.debug(f"Email sent successfully to {csv_recipient.email} ({index}/{total_recipients})")
                    else:
                        logger.error(f"Failed to send email to {csv_recipient.email}")
                    
                    # Small delay to avoid overloading email server
                    time.sleep(0.1)
                    
                except ValidationError:
                    logger.warning(f"Invalid email skipped: {csv_recipient.email}")
                    continue
                except Exception as e:
                    logger.error(f"Error sending to {csv_recipient.email}: {str(e)}")
                    continue
            
            # Update campaign status
            campaign.status = 'completed'
            campaign.completed_at = timezone.now()
            campaign.save()
            
            logger.info(f"CSV campaign '{campaign.name}' completed. Sent: {campaign.sent_count}")
        else:
            # Process regular deliveries
            deliveries = EmailDelivery.objects.filter(campaign=campaign, status='pending')
            total_deliveries = deliveries.count()
            
            for index, delivery in enumerate(deliveries, 1):
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
                    
                    # Validate email before sending
                    validate_email(email)
                    
                    # Personalize email content
                    context = {
                        'user': recipient,
                        'first_name': getattr(recipient, 'first_name', '') or '',
                        'last_name': getattr(recipient, 'last_name', '') or '',
                        'email': email,
                        'tracking_pixel': f"{settings.BASE_URL}/newsletter/track/open/{delivery.tracking_id}/",
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
                        logger.debug(f"Email sent successfully to {email} ({index}/{total_deliveries})")
                    else:
                        delivery.status = 'failed'
                        delivery.error_message = 'Failed to send email'
                        delivery.save()
                        logger.error(f"Failed to send email to {email}")
                    
                    # Small delay to avoid overloading email server
                    time.sleep(0.1)
                    
                except ValidationError:
                    logger.warning(f"Invalid email skipped: {email}")
                    delivery.status = 'failed'
                    delivery.error_message = 'Invalid email address'
                    delivery.save()
                    continue
                except Exception as e:
                    logger.error(f"Error sending to {email}: {str(e)}")
                    delivery.status = 'failed'
                    delivery.error_message = str(e)
                    delivery.save()
                    continue
            
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

@shared_task(bind=True, max_retries=3)
def process_csv_campaign_batch(self, campaign_id, batch_size=50, offset=0):
    """Process CSV campaign in batches to avoid memory issues"""
    from .models import EmailCampaign, CsvRecipient
    
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        
        if campaign.status != 'sending':
            logger.warning(f"Campaign {campaign.id} is not in 'sending' state. Current state: {campaign.status}")
            return
        
        logger.info(f"Processing CSV campaign '{campaign.name}' batch starting at {offset}")
        
        # Determine sender email
        sender_email = campaign.sender_email if campaign.sender_email else settings.DEFAULT_FROM_EMAIL
        
        # Get batch of recipients
        batch_recipients = campaign.csv_recipients.all()[offset:offset + batch_size]
        
        for csv_recipient in batch_recipients:
            try:
                # Validate email before sending
                validate_email(csv_recipient.email)
                
                # Create context with CSV data
                context = {
                    'email': csv_recipient.email,
                    **csv_recipient.data,
                    'tracking_pixel': f"{settings.BASE_URL}/newsletter/track/open/csv_{csv_recipient.id}/",
                }
                
                # Send the email
                success = send_campaign_email(campaign, csv_recipient.email, context, sender_email)
                
                if success:
                    # Update campaign stats atomically
                    EmailCampaign.objects.filter(id=campaign_id).update(
                        sent_count=models.F('sent_count') + 1
                    )
                    logger.debug(f"Email sent successfully to {csv_recipient.email}")
                else:
                    logger.error(f"Failed to send email to {csv_recipient.email}")
                
                # Small delay to avoid overloading email server
                time.sleep(0.1)
                
            except ValidationError:
                logger.warning(f"Invalid email skipped: {csv_recipient.email}")
                continue
            except Exception as e:
                logger.error(f"Error sending to {csv_recipient.email}: {str(e)}")
                continue
        
        # Check if there are more recipients to process
        total_recipients = campaign.csv_recipients.count()
        next_offset = offset + batch_size
        
        if next_offset < total_recipients:
            # Schedule next batch
            process_csv_campaign_batch.delay(campaign_id, batch_size, next_offset)
        else:
            # Final batch - update campaign status
            campaign.status = 'completed'
            campaign.completed_at = timezone.now()
            campaign.save()
            logger.info(f"CSV campaign '{campaign.name}' completed. Total sent: {campaign.sent_count}")
        
    except Exception as e:
        logger.error(f"Error processing CSV campaign batch {campaign_id}: {str(e)}")
        try:
            campaign = EmailCampaign.objects.get(id=campaign_id)
            campaign.status = 'failed'
            campaign.save()
        except:
            pass
        # Retry the task with exponential backoff
        self.retry(exc=e, countdown=60 * self.request.retries)

def send_campaign_email(campaign, recipient_email, context, sender_email):
    """Helper function to send a campaign email with improved error handling"""
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
            to=[recipient_email],
            headers={'X-Campaign-ID': str(campaign.id)}
        )
        
        # Add HTML content with tracking pixel if available
        if html_content:
            tracking_pixel = context.get('tracking_pixel', '')
            if tracking_pixel:
                tracking_img = f'<img src="{tracking_pixel}" width="1" height="1" alt="" style="display:none;">'
                html_with_tracking = html_content + tracking_img
            else:
                html_with_tracking = html_content
            
            msg.attach_alternative(html_with_tracking, "text/html")
        
        # Send email
        msg.send()
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email to {recipient_email}: {str(e)}")
        return False

# Legacy tasks for backward compatibility
@shared_task
def process_csv_campaign(campaign_id):
    """Legacy task - delegates to main process_email_campaign"""
    return process_email_campaign.delay(campaign_id)

@shared_task
def send_single_csv_email(campaign_id, csv_recipient_id):
    """Send email to a single CSV recipient with validation"""
    from .models import EmailCampaign, CsvRecipient
    
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        csv_recipient = CsvRecipient.objects.get(id=csv_recipient_id)
        
        # Validate email before sending
        validate_email(csv_recipient.email)
        
        # Determine sender email
        sender_email = campaign.sender_email if campaign.sender_email else settings.DEFAULT_FROM_EMAIL
        
        # Create context with CSV data
        context = {
            'email': csv_recipient.email,
            **csv_recipient.data,
            'tracking_pixel': f"{settings.BASE_URL}/newsletter/track/open/csv_{csv_recipient.id}/",
        }
        
        # Send the email
        success = send_campaign_email(campaign, csv_recipient.email, context, sender_email)
        
        if success:
            # Update campaign stats atomically
            EmailCampaign.objects.filter(id=campaign_id).update(
                sent_count=models.F('sent_count') + 1
            )
            logger.info(f"Email sent to {csv_recipient.email}")
            return True
        else:
            logger.error(f"Failed to send email to {csv_recipient.email}")
            return False
            
    except ValidationError:
        logger.warning(f"Invalid email skipped: {csv_recipient.email}")
        return False
    except Exception as e:
        logger.error(f"Error in send_single_csv_email: {str(e)}")
        return False