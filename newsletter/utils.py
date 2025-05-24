from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_welcome_email(email, name=''):
    """
    Send a welcome email to new newsletter subscribers.
    
    Args:
        email (str): The recipient's email address
        name (str, optional): The recipient's name. Defaults to empty string.
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        subject = "Welcome to the TTU Lab Management System Newsletter"
        
        # Personalize greeting if name is provided
        greeting = f"Hi {name}," if name else "Hi there,"
        
        # Create HTML content from template
        html_content = render_to_string('newsletter/welcome_email.html', {
            'name': name,
            'greeting': greeting,
        })
        
        # Create plain text version
        text_content = strip_tags(html_content)
        
        # Create message
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            f"TTU Lab System <{settings.DEFAULT_FROM_EMAIL}>",
            [email]
        )
        
        # Attach HTML content
        msg.attach_alternative(html_content, "text/html")
        
        # Send email
        msg.send()
        logger.info(f"Welcome email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending welcome email to {email}: {str(e)}")
        return False

def send_newsletter(subject, template_name, recipients, context=None):
    """
    Send a newsletter to multiple recipients using a template.
    
    Args:
        subject (str): Email subject
        template_name (str): Name of the HTML template to use
        recipients (list): List of email addresses to send to
        context (dict, optional): Context to pass to the template. Defaults to None.
    
    Returns:
        int: Number of emails sent successfully
    """
    if context is None:
        context = {}
        
    successful_sends = 0
    
    # Create HTML content from template
    html_content = render_to_string(f'newsletter/{template_name}', context)
    
    # Create plain text version
    text_content = strip_tags(html_content)
    
    try:
        # Send to each recipient individually to personalize
        for recipient in recipients:
            try:
                # Create message
                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    f"TTU Lab System <{settings.DEFAULT_FROM_EMAIL}>",
                    [recipient]
                )
                
                # Attach HTML content
                msg.attach_alternative(html_content, "text/html")
                
                # Send email
                msg.send()
                successful_sends += 1
                logger.info(f"Newsletter sent to {recipient}")
                
            except Exception as e:
                logger.error(f"Error sending newsletter to {recipient}: {str(e)}")
    
    except Exception as e:
        logger.error(f"General error sending newsletter: {str(e)}")
    
    return successful_sends

def unsubscribe_user(email_or_token):
    """
    Handle user unsubscription requests
    
    Args:
        email_or_token (str): Email address or unsubscribe token
    
    Returns:
        bool: True if unsubscribed successfully, False otherwise
    """
    from .models import NewsletterSubscription
    
    try:
        # Try to find by email first
        subscription = NewsletterSubscription.objects.filter(email=email_or_token).first()
        
        # If not found by email, try to find by token
        if not subscription:
            subscription = NewsletterSubscription.objects.filter(unsubscribe_token=email_or_token).first()
            
        if subscription:
            subscription.is_active = False
            subscription.save()
            
            # Send confirmation email
            send_mail(
                "You've been unsubscribed",
                f"You have been successfully unsubscribed from the TTU Lab Management System newsletter. "
                f"If you wish to subscribe again in the future, please visit our website.",
                settings.DEFAULT_FROM_EMAIL,
                [subscription.email]
            )
            
            return True
        return False
        
    except Exception as e:
        logger.error(f"Error unsubscribing user {email_or_token}: {str(e)}")
        return False

def get_active_subscribers(categories=None):
    """
    Get a list of active subscribers, optionally filtered by subscription categories.
    
    Args:
        categories (list, optional): List of category names to filter by. 
            Options: 'updates', 'lab_news', 'tips', 'events'
            
    Returns:
        QuerySet: Filtered NewsletterSubscription objects
    """
    from .models import NewsletterSubscription
    
    subscribers = NewsletterSubscription.objects.filter(is_active=True)
    
    if categories:
        filter_kwargs = {}
        if 'updates' in categories:
            filter_kwargs['receive_updates'] = True
        if 'lab_news' in categories:
            filter_kwargs['receive_lab_news'] = True
        if 'tips' in categories:
            filter_kwargs['receive_tips'] = True
        if 'events' in categories:
            filter_kwargs['receive_events'] = True
            
        if filter_kwargs:
            subscribers = subscribers.filter(**filter_kwargs)
    
    return subscribers