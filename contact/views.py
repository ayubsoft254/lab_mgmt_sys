from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ContactSubmission
from django.core.mail import send_mail
from django.conf import settings

def contact_submit(request):
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
            recipient_list=[settings.ADMIN_EMAIL],  # Add ADMIN_EMAIL in settings.py
            fail_silently=False,
        )
        
        # Show success message
        messages.success(request, "Your message has been sent. We'll get back to you soon!")
        return redirect('landing')
    
    # If not POST, redirect to the landing page
    return redirect('landing')
