from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import User, LabResource, Booking, Ticket
from django.core.exceptions import ValidationError

# Landing page view
def landing_page(request):
    return render(request, 'landing_page.html')

# Dashboard view
@login_required
def dashboard(request):
    user = request.user
    bookings = Booking.objects.filter(user=user)
    tickets = Ticket.objects.filter(created_by=user)
    labs = LabResource.objects.values('lab').distinct()  # Get unique labs

    context = {
        'bookings': bookings,
        'tickets': tickets,
        'labs': labs,
    }
    return render(request, 'dashboard.html', context)

# View to list available computers in a lab
@login_required
def list_lab_computers(request, lab_name):
    computers = LabResource.objects.filter(lab=lab_name, is_available=True)
    context = {
        'lab_name': lab_name,
        'computers': computers,
    }
    return render(request, 'lab_computers.html', context)

# View to book a computer
@login_required
def book_computer(request, computer_id):
    computer = get_object_or_404(LabResource, id=computer_id)
    if request.method == 'POST':
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        # Ensure the computer is available
        if not computer.is_available:
            messages.error(request, "This computer is no longer available.")
            return redirect('list_lab_computers', lab_name=computer.lab)

        # Create a new booking
        booking = Booking(
            user=request.user,
            resource=computer,
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )

        try:
            booking.full_clean()  # Validate the booking
            booking.save()
            computer.is_available = False
            computer.save()
            messages.success(request, "Booking successful! Your booking is pending confirmation.")
        except ValidationError as e:
            messages.error(request, f"Booking failed: {e.messages[0]}")
        
        return redirect('list_lab_computers', lab_name=computer.lab)

    context = {
        'computer': computer,
    }
    return render(request, 'book_computer.html', context)

# View to list a user's bookings
@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user)
    context = {
        'bookings': bookings,
    }
    return render(request, 'my_bookings.html', context)

# View to cancel a booking
@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.status == 'confirmed':
        booking.resource.is_available = True
        booking.resource.save()
    booking.delete()
    messages.success(request, "Booking canceled successfully.")
    return redirect('my_bookings')

# View to create a ticket
@login_required
def create_ticket(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority')

        ticket = Ticket(
            title=title,
            description=description,
            created_by=request.user,
            priority=priority,
            status='open'
        )
        ticket.save()
        messages.success(request, "Ticket created successfully.")
        return redirect('view_tickets')

    return render(request, 'create_ticket.html')

# View to list all tickets
@login_required
def view_tickets(request):
    tickets = Ticket.objects.filter(created_by=request.user)
    context = {
        'tickets': tickets,
    }
    return render(request, 'view_tickets.html', context)

# View to update a ticket's status (e.g., mark as resolved)
@login_required
def update_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, created_by=request.user)
    if request.method == 'POST':
        status = request.POST.get('status')
        ticket.status = status
        ticket.save()
        messages.success(request, "Ticket status updated successfully.")
        return redirect('view_tickets')

    context = {
        'ticket': ticket,
    }
    return render(request, 'update_ticket.html', context)