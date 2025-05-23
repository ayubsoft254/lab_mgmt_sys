from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from booking.views import landing_view
from analytics import views as analytics_views
from contact.views import contact_submit

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('booking.urls')),
    path('analytics/', analytics_views.analytics_dashboard_view, name='analytics_dashboard'),
    path('contact/submit/', contact_submit, name='contact_submit'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
