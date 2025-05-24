from django.urls import path
from . import views
from .views import LandingPageView

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing'),
    path('home', views.home_view, name='home'),
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
    path('notifications/unread/json/', views.unread_notifications_json, name='unread_notifications_json'),
    path('recurring-booking/', views.recurring_booking_view, name='recurring_booking'),
    path('free-timeslots/', views.free_timeslots_view, name='free_timeslots'),   
    path('labs/<int:lab_id>/free-timeslots/', views.free_timeslots_view, name='lab_free_timeslots'),
    path('computers/<int:computer_id>/free-timeslots/', views.free_timeslots_view, name='computer_free_timeslots'),    
    path('recurring/sessions/', views.recurring_sessions_list_view, name='recurring_sessions_list'),
    path('recurring-session/<int:session_id>/cancel/', views.cancel_recurring_session_view, name='cancel_recurring_session'),
    path('recurring-session/<int:session_id>/approve/', views.approve_recurring_session_view, name='approve_recurring_session'),
    path('recurring-session/<int:session_id>/reject/', views.reject_recurring_session_view, name='reject_recurring_session'),

    # Bulk actions
    path('admin/bulk-approve-bookings/', views.bulk_approve_bookings_view, name='bulk_approve_bookings'),
    path('admin/bulk-approve-sessions/', views.bulk_approve_sessions_view, name='bulk_approve_sessions'),
    path('admin/bulk-approve-recurring-sessions/', views.bulk_approve_recurring_sessions_view, name='bulk_approve_recurring_sessions'),
    path('admin/bulk-cancel-bookings/', views.bulk_cancel_bookings_view, name='bulk_cancel_bookings'),
    path('admin/bulk-cancel-sessions/', views.bulk_cancel_sessions_view, name='bulk_cancel_sessions'),
    path('admin/bulk-cancel-recurring-sessions/', views.bulk_cancel_recurring_sessions_view, name='bulk_cancel_recurring_sessions'),

    # Individual actions
    path('booking/<int:booking_id>/reject/', views.reject_booking_view, name='reject_booking'),
    path('session/<int:session_id>/reject/', views.reject_session_view, name='reject_session'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    path('session/<int:session_id>/cancel/', views.cancel_session_view, name='cancel_session'),  
    path('students/<int:student_id>/rate/session/<int:session_id>/', views.rate_student_view, name='rate_student_session'),
    path('students/<int:student_id>/rate/booking/<int:booking_id>/', views.rate_student_view, name='rate_student_booking'),

    # API endpoints
    path('api/sessions/<int:session_id>/details/', views.session_details_api, name='session_details_api'),
    path('api/bookings/<int:booking_id>/details/', views.booking_details_api, name='booking_details_api'),
    path('students/<int:student_id>/details/', views.student_details_view, name='student_details'),
    path('students/<int:student_id>/rate/', views.rate_student_view, name='rate_student'),

    # Add this to your existing URLs
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('booking/<int:booking_id>/extend/', views.extend_booking, name='extend_booking'),

    # Check-in URLs
    path('admin/check-in/', views.admin_check_in_dashboard, name='admin_check_in_dashboard'),
    path('admin/check-in/booking/<int:booking_id>/', views.computer_booking_check_in, name='computer_booking_check_in'),
    path('admin/check-in/session/<int:session_id>/', views.lab_session_attendance, name='lab_session_attendance'),
    path('admin/check-in/quick/<int:booking_id>/', views.quick_check_in, name='quick_check_in'),
]