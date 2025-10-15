from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags

from .models import ContactSubmission, Inquiry, Feedback
from .forms import InquiryForm, FeedbackForm


def contact_submit(request):
    """Legacy contact form submission for backward compatibility"""
    if request.method == 'POST':
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        
        # Validate inputs
        if not all([name, email, subject, message]):
            messages.error(request, "Please fill in all the fields.")
            return redirect('landing')
        
        # Store submission in database
        ContactSubmission.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        
        # Send notification email to admin
        send_mail(
            subject=f'New Contact Form Submission: {subject}',
            message=f'Name: {name}\nEmail: {email}\nSubject: {subject}\n\nMessage:\n{message}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_USER_EMAIL],
            fail_silently=False,
        )
        
        # Show success message
        messages.success(request, "Your message has been sent. We'll get back to you soon!")
        return redirect('landing')
    
    # If not POST, redirect to the landing page
    return redirect('landing')


@require_http_methods(["GET", "POST"])
def submit_inquiry(request):
    """Handle inquiry submissions"""
    if request.method == 'POST':
        form = InquiryForm(request.POST)
        
        if form.is_valid():
            inquiry = form.save(commit=False)
            
            # Associate with logged-in user if available
            if request.user.is_authenticated:
                inquiry.user = request.user
            
            inquiry.save()
            
            # Send confirmation email to user
            _send_inquiry_confirmation_email(inquiry)
            
            # Send notification email to admin
            _send_inquiry_admin_notification(inquiry)
            
            messages.success(
                request,
                "Your inquiry has been submitted successfully! We'll review it and get back to you soon."
            )
            return redirect('inquiry_success')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = InquiryForm()
    
    context = {
        'form': form,
        'form_type': 'inquiry',
        'title': 'Submit an Inquiry',
        'description': 'Have a question? Send us your inquiry and we\'ll get back to you as soon as possible.',
    }
    
    return render(request, 'contact/inquiry_form.html', context)


@require_http_methods(["GET", "POST"])
def submit_feedback(request):
    """Handle feedback submissions"""
    if request.method == 'POST':
        form = FeedbackForm(request.POST, user=request.user)
        
        if form.is_valid():
            feedback = form.save(commit=False)
            
            # Associate with logged-in user if available
            if request.user.is_authenticated:
                feedback.user = request.user
            
            feedback.save()
            
            # Send confirmation email to user (if email provided)
            _send_feedback_confirmation_email(feedback)
            
            # Send notification email to admin
            _send_feedback_admin_notification(feedback)
            
            messages.success(
                request,
                "Thank you for your feedback! Your input helps us improve the system."
            )
            return redirect('feedback_success')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = FeedbackForm(user=request.user)
    
    context = {
        'form': form,
        'form_type': 'feedback',
        'title': 'Share Your Feedback',
        'description': 'We value your feedback and would love to hear your thoughts about our system.',
    }
    
    return render(request, 'contact/feedback_form.html', context)


def inquiry_success(request):
    """Success page after inquiry submission"""
    return render(request, 'contact/inquiry_success.html')


def feedback_success(request):
    """Success page after feedback submission"""
    return render(request, 'contact/feedback_success.html')


@login_required
def inquiry_detail(request, pk):
    """View inquiry details (for users who submitted it)"""
    inquiry = get_object_or_404(Inquiry, pk=pk)
    
    # Check if user has permission to view this inquiry
    if inquiry.user != request.user and not request.user.is_admin:
        messages.error(request, "You don't have permission to view this inquiry.")
        return redirect('home')
    
    context = {
        'inquiry': inquiry,
    }
    
    return render(request, 'contact/inquiry_detail.html', context)


@login_required
def my_inquiries(request):
    """View all user's inquiries"""
    if not request.user.is_authenticated:
        return redirect('account_login')
    
    inquiries = Inquiry.objects.filter(user=request.user)
    
    context = {
        'inquiries': inquiries,
    }
    
    return render(request, 'contact/my_inquiries.html', context)


# Email helper functions
def _send_inquiry_confirmation_email(inquiry):
    """Send confirmation email to user who submitted inquiry"""
    try:
        subject = f'Your Inquiry Received - {inquiry.subject}'
        
        context = {
            'inquiry': inquiry,
            'support_email': settings.ADMIN_USER_EMAIL,
            'base_url': settings.BASE_URL,
        }
        
        html_message = render_to_string('emails/inquiry_confirmation.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[inquiry.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending inquiry confirmation email: {e}")


def _send_inquiry_admin_notification(inquiry):
    """Send notification email to admin about new inquiry"""
    try:
        subject = f'New Inquiry Submitted - {inquiry.subject}'
        
        context = {
            'inquiry': inquiry,
            'inquiry_detail_url': f"{settings.BASE_URL}/admin/contact/inquiry/{inquiry.pk}/change/",
        }
        
        html_message = render_to_string('emails/inquiry_admin_notification.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_USER_EMAIL],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending inquiry admin notification: {e}")


def _send_feedback_confirmation_email(feedback):
    """Send confirmation email to user who submitted feedback"""
    try:
        subject = 'Your Feedback Has Been Received'
        
        context = {
            'feedback': feedback,
            'support_email': settings.ADMIN_USER_EMAIL,
            'base_url': settings.BASE_URL,
        }
        
        html_message = render_to_string('emails/feedback_confirmation.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[feedback.email] if feedback.email else [],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending feedback confirmation email: {e}")


def _send_feedback_admin_notification(feedback):
    """Send notification email to admin about new feedback"""
    try:
        subject = f'New Feedback Submitted - {feedback.title}'
        
        context = {
            'feedback': feedback,
            'feedback_detail_url': f"{settings.BASE_URL}/admin/contact/feedback/{feedback.pk}/change/",
        }
        
        html_message = render_to_string('emails/feedback_admin_notification.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_USER_EMAIL],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending feedback admin notification: {e}")
