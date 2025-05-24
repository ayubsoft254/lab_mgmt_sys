from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from analytics.views import AnalyticsView, AnalyticsApiView
from contact.views import contact_submit
from newsletter.admin import newsletter_stats_view  # Replace 'your_app' with the actual app name where newsletter_stats_view is defined
from newsletter import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('booking.urls')),
    path('analytics/', AnalyticsView.as_view(), name='analytics_dashboard'),
    path('analytics/api/', AnalyticsApiView.as_view(), name='analytics_api'),
    path('contact/submit/', contact_submit, name='contact_submit'),
    path('newsletter-stats/', admin.site.admin_view(newsletter_stats_view), name='newsletter_stats'),
    path('subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),
    path('unsubscribe/<uuid:token>/', views.unsubscribe, name='unsubscribe'),
    path('track/open/<uuid:tracking_id>/', views.track_email_open, name='track_email_open'),
    path('track/click/<uuid:tracking_id>/<path:redirect_url>/', views.track_email_click, name='track_email_click'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
