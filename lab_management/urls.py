from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),    
    path('lab/<str:lab_name>/', views.list_lab_computers, name='list_lab_computers'),
    path('book/<int:computer_id>/', views.book_computer, name='book_computer'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('create-ticket/', views.create_ticket, name='create_ticket'),
    path('view-tickets/', views.view_tickets, name='view_tickets'),
    path('update-ticket/<int:ticket_id>/', views.update_ticket, name='update_ticket'),

]
