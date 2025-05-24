from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from analytics.views import AnalyticsView, AnalyticsApiView
from contact.views import contact_submit

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('booking.urls')),
    path('analytics/', AnalyticsView.as_view(), name='analytics_dashboard'),
    path('analytics/api/', AnalyticsApiView.as_view(), name='analytics_api'),
    path('contact/submit/', contact_submit, name='contact_submit'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
