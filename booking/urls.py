from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('labs/', views.lab_list_view, name='lab_list'),
    path('labs/<int:lab_id>/', views.lab_detail_view, name='lab_detail'),
    path('labs/<int:lab_id>/book/', views.student_booking_view, name='student_booking'),
    path('labs/<int:lab_id>/computers/<int:computer_id>/book/', views.student_booking_view, name='computer_booking'),
    path('lecturer/book/', views.lecturer_booking_view, name='lecturer_booking'),
    path('booking/<int:booking_id>/success/', views.booking_success_view, name='booking_success'),
    path('Dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('Dashboard/bookings/<int:booking_id>/approve/', views.approve_booking_view, name='approve_booking'),
    path('Dashboard/sessions/<int:session_id>/approve/', views.approve_session_view, name='approve_session'),
    path('notifications/', views.notification_list_view, name='notification_list'),
]