from django.urls import path
from .views import DocumentationView

urlpatterns = [
    # Other URLs in your resources app
    path('documentation/', DocumentationView.as_view(), name='documentation'),
]