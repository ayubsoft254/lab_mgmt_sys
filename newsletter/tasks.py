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

@shared_task
def debug_test_task():
    """Simple test task to verify Celery is working"""
    logger.info("DEBUG: Test task executed successfully!")
    return "Test task completed at {}".format(timezone.now())

@shared_task
def process_email_campaign(campaign_id):
    """Process an email campaign by sending emails to all recipients with comprehensive debugging"""
    from .models import EmailCampaign, EmailDelivery, CsvRecipient
    
    try:
        logger.info("DEBUG: Starting process_email_campaign for campaign_id: {}".format(campaign_id))
        
        campaign = EmailCampaign.objects.get(id=campaign_id)
        logger.info("DEBUG: Found campaign: {} with status: {}".format(campaign.name, campaign.status))
        
        if campaign.status != 'sending':
            logger.warning("Campaign {} is not in 'sending' state. Current state: {}".format(
                campaign.id, campaign.status))
            return "Campaign not in sending state"
        
        logger.info("Processing campaign '{}' with {} recipients".format(
            campaign.name, campaign.total_recipients))
        
        # Determine sender email
        sender_email = campaign.sender_email if campaign.sender_email else getattr(settings, 'DEFAULT_FROM_EMAIL', 'test@example.com')
        logger.info("DEBUG: Using sender email: {}".format(sender_email))
        
        if campaign.recipient_type == 'csv_upload':
            logger.info("DEBUG: Processing CSV campaign")
            
            # Process CSV recipients
            csv_recipients = campaign.csv_recipients.all()
            total_recipients = csv_recipients.count()
            logger.info("DEBUG: Found {} CSV recipients".format(total_recipients))
            
            if total_recipients == 0:
                logger.error("DEBUG: No CSV recipients found!")
                campaign.status = 'failed'
                campaign.save()
                return "No CSV recipients found"
            
            # Check if campaign has content
            if not campaign.html_content and not campaign.text_content:
                logger.error("DEBUG: Campaign has no content! html_content: '{}', text_content: '{}'".format(
                    campaign.html_content or 'None', campaign.text_content or 'None'))
                campaign.status = 'failed'
                campaign.save()
                return "Campaign has no content"
            
            successful_sends = 0
            failed_sends = 0
            
            for index, csv_recipient in enumerate(csv_recipients, 1):
                try:
                    logger.info("DEBUG: Processing recipient {}/{}: {}".format(index, total_recipients, csv_recipient.email))
                    
                    # Validate email before sending
                    validate_email(csv_recipient.email)
                    logger.info("DEBUG: Email validation passed for {}".format(csv_recipient.email))
                    
                    # Create context with CSV data
                    context = {
                        'email': csv_recipient.email,
                        **csv_recipient.data,
                        'tracking_pixel': "{}/newsletter/track/open/csv_{}/".format(
                            getattr(settings, 'BASE_URL', 'http://localhost:8000'),
                            csv_recipient.id
                        ),
                    }
                    logger.info("DEBUG: Context for {}: {}".format(csv_recipient.email, context))
                    
                    # Send the email
                    success = send_campaign_email(campaign, csv_recipient.email, context, sender_email)
                    logger.info("DEBUG: Email send result for {}: {}".format(csv_recipient.email, success))
                    
                    if success:
                        successful_sends += 1
                        # Update campaign stats atomically
                        EmailCampaign.objects.filter(id=campaign_id).update(
                            sent_count=models.F('sent_count') + 1
                        )
                        logger.info("Email sent successfully to {} ({}/{})".format(
                            csv_recipient.email, index, total_recipients))
                    else:
                        failed_sends += 1
                        logger.error("Failed to send email to {}".format(csv_recipient.email))
                    
                    # Small delay to avoid overloading email server
                    time.sleep(0.1)
                    
                except ValidationError as ve:
                    failed_sends += 1
                    logger.warning("Invalid email skipped: {} - Error: {}".format(csv_recipient.email, str(ve)))
                    continue
                except Exception as e:
                    failed_sends += 1
                    logger.error("Error sending to {}: {}".format(csv_recipient.email, str(e)))
                    import traceback
                    logger.error("DEBUG: Traceback: {}".format(traceback.format_exc()))
                    continue
            
            # Update campaign status
            campaign.refresh_from_db()
            campaign.status = 'completed'
            campaign.completed_at = timezone.now()
            campaign.save()
            
            final_message = "CSV campaign '{}' completed. Successful: {}, Failed: {}, Total sent count: {}".format(
                campaign.name, successful_sends, failed_sends, campaign.sent_count)
            logger.info(final_message)
            return final_message
            
        else:
            logger.info("DEBUG: Processing regular campaign")
            # Process regular deliveries
            deliveries = EmailDelivery.objects.filter(campaign=campaign, status='pending')
            total_deliveries = deliveries.count()
            logger.info("DEBUG: Found {} pending deliveries".format(total_deliveries))
            
            successful_sends = 0
            failed_sends = 0
            
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
                        failed_sends += 1
                        continue
                    
                    # Validate email before sending
                    validate_email(email)
                    
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
                        successful_sends += 1
                        # Update delivery status
                        delivery.status = 'sent'
                        delivery.sent_at = timezone.now()
                        delivery.save()
                        
                        # Update campaign stats atomically
                        EmailCampaign.objects.filter(id=campaign_id).update(
                            sent_count=models.F('sent_count') + 1
                        )
                        logger.info("Email sent successfully to {} ({}/{})".format(email, index, total_deliveries))
                    else:
                        failed_sends += 1
                        delivery.status = 'failed'
                        delivery.error_message = 'Failed to send email'
                        delivery.save()
                        logger.error("Failed to send email to {}".format(email))
                    
                    # Small delay to avoid overloading email server
                    time.sleep(0.1)
                    
                except ValidationError as ve:
                    failed_sends += 1
                    logger.warning("Invalid email skipped: {} - Error: {}".format(email, str(ve)))
                    delivery.status = 'failed'
                    delivery.error_message = 'Invalid email address'
                    delivery.save()
                    continue
                except Exception as e:
                    failed_sends += 1
                    logger.error("Error sending to {}: {}".format(email, str(e)))
                    delivery.status = 'failed'
                    delivery.error_message = str(e)
                    delivery.save()
                    continue
            
            # Update campaign status
            campaign.refresh_from_db()
            campaign.status = 'completed'
            campaign.completed_at = timezone.now()
            campaign.save()
            
            final_message = "Campaign '{}' completed. Successful: {}, Failed: {}, Total sent count: {}".format(
                campaign.name, successful_sends, failed_sends, campaign.sent_count)
            logger.info(final_message)
            return final_message
        
    except EmailCampaign.DoesNotExist:
        error_msg = "Campaign with ID {} not found".format(campaign_id)
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = "Error processing campaign {}: {}".format(campaign_id, str(e))
        logger.error(error_msg)
        import traceback
        logger.error("DEBUG: Full traceback: {}".format(traceback.format_exc()))
        try:
            campaign = EmailCampaign.objects.get(id=campaign_id)
            campaign.status = 'failed'
            campaign.save()
        except:
            pass
        return error_msg

def send_campaign_email(campaign, recipient_email, context, sender_email):
    """Helper function to send a campaign email with comprehensive debugging"""
    try:
        logger.info("DEBUG: send_campaign_email called for {}".format(recipient_email))
        
        # Check if campaign has content
        if not campaign.html_content and not campaign.text_content:
            logger.error("DEBUG: Campaign has no content! html_content: '{}', text_content: '{}'".format(
                campaign.html_content or 'None', campaign.text_content or 'None'))
            return False
        
        # Check if subject exists
        if not campaign.subject:
            logger.error("DEBUG: Campaign has no subject!")
            return False
        
        # Render subject and content with context
        try:
            subject = Template(campaign.subject).render(Context(context))
            logger.info("DEBUG: Rendered subject: {}".format(subject))
        except Exception as e:
            logger.error("DEBUG: Error rendering subject: {}".format(str(e)))
            return False
            
        try:
            text_content = Template(campaign.text_content or '').render(Context(context))
            logger.info("DEBUG: Rendered text length: {}".format(len(text_content)))
        except Exception as e:
            logger.error("DEBUG: Error rendering text content: {}".format(str(e)))
            text_content = ''
            
        try:
            html_content = Template(campaign.html_content or '').render(Context(context))
            logger.info("DEBUG: Rendered html length: {}".format(len(html_content)))
        except Exception as e:
            logger.error("DEBUG: Error rendering html content: {}".format(str(e)))
            html_content = ''
        
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
                tracking_img = '<img src="{}" width="1" height="1" alt="" style="display:none;">'.format(tracking_pixel)
                html_with_tracking = html_content + tracking_img
            else:
                html_with_tracking = html_content
            
            msg.attach_alternative(html_with_tracking, "text/html")
        
        logger.info("DEBUG: About to send email to {} from {}".format(recipient_email, sender_email))
        
        # Check email backend
        from django.core.mail import get_connection
        connection = get_connection()
        logger.info("DEBUG: Email backend: {}".format(type(connection).__name__))
        
        # Send email
        result = msg.send()
        logger.info("DEBUG: Email send result: {}".format(result))
        
        if result == 1:
            logger.info("Email sent successfully to {}".format(recipient_email))
            return True
        else:
            logger.error("Email send failed (result: {}) to {}".format(result, recipient_email))
            return False
        
    except Exception as e:
        logger.error("Error sending email to {}: {}".format(recipient_email, str(e)))
        import traceback
        logger.error("DEBUG: Email send traceback: {}".format(traceback.format_exc()))
        return False

@shared_task
def process_csv_campaign_batch(campaign_id, batch_size=50):
    """Process CSV campaign in batches - delegates to main task"""
    return process_email_campaign.delay(campaign_id)

# Legacy tasks for backward compatibility
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
        
        # Validate email before sending
        validate_email(csv_recipient.email)
        
        # Determine sender email
        sender_email = campaign.sender_email if campaign.sender_email else getattr(settings, 'EMAIL_HOST_USER', 'test@example.com')
        
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
            
    except ValidationError:
        logger.warning("Invalid email skipped: {}".format(csv_recipient.email if 'csv_recipient' in locals() else 'unknown'))
        return False
    except Exception as e:
        logger.error("Error in send_single_csv_email: {}".format(str(e)))
        return False