from django.urls import path
from .views import DocumentationView, TermsConditionsView

urlpatterns = [
    # Other URLs in your resources app
    path('documentation/', DocumentationView.as_view(), name='documentation'),
    path('terms/', TermsConditionsView.as_view(), name='terms_conditions'),
]