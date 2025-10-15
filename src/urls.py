from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from analytics.views import AnalyticsView, AnalyticsApiView
from newsletter import views
from newsletter.admin import admin_stats_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('booking.urls')),
    path('contact/', include('contact.urls')),
    path('analytics/', AnalyticsView.as_view(), name='analytics_dashboard'),
    path('analytics/api/', AnalyticsApiView.as_view(), name='analytics_api'),
    path('newsletter-stats/', admin.site.admin_view(admin_stats_view), name='newsletter_stats'),
    path('subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),
    path('unsubscribe/<uuid:token>/', views.unsubscribe, name='unsubscribe'),
    path('track/open/<uuid:tracking_id>/', views.track_email_open, name='track_email_open'),
    path('track/click/<uuid:tracking_id>/<path:redirect_url>/', views.track_email_click, name='track_email_click'),
    path('resources/', include('resources.urls')),    
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler400 = 'src.views.bad_request'
handler403 = 'src.views.permission_denied'
handler404 = 'src.views.page_not_found'
handler500 = 'src.views.server_error'
