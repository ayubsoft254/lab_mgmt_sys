from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ContactSubmission

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
        
        # Send notification email to admin (optional)
        # send_mail(...)
        
        # Show success message
        messages.success(request, "Your message has been sent. We'll get back to you soon!")
        return redirect('landing')
    
    # If not POST, redirect to the landing page
    return redirect('landing')
