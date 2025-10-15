from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    # Legacy contact form
    path('submit/', views.contact_submit, name='contact_submit'),
    
    # Inquiry endpoints
    path('inquiries/submit/', views.submit_inquiry, name='submit_inquiry'),
    path('inquiries/success/', views.inquiry_success, name='inquiry_success'),
    path('inquiries/<int:pk>/', views.inquiry_detail, name='inquiry_detail'),
    path('inquiries/my/', views.my_inquiries, name='my_inquiries'),
    
    # Feedback endpoints
    path('feedback/submit/', views.submit_feedback, name='submit_feedback'),
    path('feedback/success/', views.feedback_success, name='feedback_success'),
]
