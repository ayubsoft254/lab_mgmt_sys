"""
URL configuration for lab_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
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
