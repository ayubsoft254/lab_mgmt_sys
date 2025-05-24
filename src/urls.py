from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from analytics.views import AnalyticsView, AnalyticsApiView
from contact.views import contact_submit
from newsletter.admin import newsletter_stats_view  # Replace 'your_app' with the actual app name where newsletter_stats_view is defined

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('booking.urls')),
    path('analytics/', AnalyticsView.as_view(), name='analytics_dashboard'),
    path('analytics/api/', AnalyticsApiView.as_view(), name='analytics_api'),
    path('contact/submit/', contact_submit, name='contact_submit'),
# Import your newsletter_stats_view at the top of the file:
# from your_app.admin import newsletter_stats_view
path(
    'newsletter-stats/',
    admin.site.admin_view(newsletter_stats_view),
    name='newsletter_stats',
),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
