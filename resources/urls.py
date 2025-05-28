from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # Other URLs in your resources app
    path('documentation/', views.DocumentationView.as_view(), name='documentation'),
    path('terms/', views.TermsConditionsView.as_view(), name='terms_conditions'),
    path('privacy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('feedback/', views.FeedbackFormView.as_view(), name='feedback_form'),
    path('feedback/success/', TemplateView.as_view(template_name='feedback_success.html'), 
         name='feedback_success'),
    path('api/feedback/submit/', views.ajax_feedback_submit, name='ajax_feedback_submit'),
]