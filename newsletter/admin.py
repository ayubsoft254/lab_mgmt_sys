from django.contrib import admin
from .models import NewsletterSubscription
from django.utils.html import format_html
from django.urls import reverse
from django import forms
from django.contrib import messages
import csv
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone

class NewsletterSubscriptionAdminForm(forms.ModelForm):
    """Custom form for NewsletterSubscription admin"""
    class Meta:
        model = NewsletterSubscription
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'size': '40'}),
            'email': forms.EmailInput(attrs={'size': '40'}),
        }

@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    form = NewsletterSubscriptionAdminForm
    list_display = ('email', 'name', 'subscription_status', 'preference_summary', 'subscription_date', 'actions_column')
    list_filter = ('is_active', 'receive_updates', 'receive_lab_news', 'receive_tips', 'receive_events', 'source', 'created_at')
    search_fields = ('email', 'name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Subscriber Information', {
            'fields': ('email', 'name', 'is_active', 'created_at')
        }),
        ('Preferences', {
            'fields': ('receive_updates', 'receive_lab_news', 'receive_tips', 'receive_events')
        }),
        ('Source Information', {
            'fields': ('source', 'unsubscribe_token')
        }),
    )
    actions = ['export_subscribers_csv', 'mark_as_inactive', 'mark_as_active']
    
    def subscription_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    subscription_date.short_description = 'Subscribed On'
    
    def subscription_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">Active</span>')
        return format_html('<span style="color: red;">Inactive</span>')
    subscription_status.short_description = 'Status'
    
    def preference_summary(self, obj):
        preferences = []
        if obj.receive_updates:
            preferences.append('Updates')
        if obj.receive_lab_news:
            preferences.append('News')
        if obj.receive_tips:
            preferences.append('Tips')
        if obj.receive_events:
            preferences.append('Events')
            
        if not preferences:
            return format_html('<span style="color: #999;">None</span>')
        return format_html('<span style="color: #666;">{}</span>', ', '.join(preferences))
    preference_summary.short_description = 'Preferences'
    
    def actions_column(self, obj):
        """Custom column for actions buttons"""
        send_email_url = reverse('admin:send_test_email', args=[obj.pk])
        toggle_url = reverse('admin:toggle_subscription', args=[obj.pk])
        
        if obj.is_active:
            toggle_text = 'Unsubscribe'
            toggle_class = 'danger'
        else:
            toggle_text = 'Reactivate'
            toggle_class = 'success'
            
        return format_html(
            '<a class="button" href="{}" title="Send test email">📧</a> '
            '<a class="button btn-{}" href="{}" title="{}">{}</a>',
            send_email_url, toggle_class, toggle_url, toggle_text, toggle_text
        )
    actions_column.short_description = 'Actions'
    
    def get_readonly_fields(self, request, obj=None):
        """Make email field read-only when editing existing object"""
        if obj:  # editing an existing object
            return self.readonly_fields + ('email', 'unsubscribe_token')
        return self.readonly_fields
    
    def export_subscribers_csv(self, request, queryset):
        """Export selected subscribers to CSV file"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="newsletter_subscribers.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Email', 'Name', 'Status', 'Updates', 'Lab News', 'Tips', 'Events', 'Source', 'Subscribed On'])
        
        for subscriber in queryset:
            writer.writerow([
                subscriber.email,
                subscriber.name,
                'Active' if subscriber.is_active else 'Inactive',
                'Yes' if subscriber.receive_updates else 'No',
                'Yes' if subscriber.receive_lab_news else 'No',
                'Yes' if subscriber.receive_tips else 'No',
                'Yes' if subscriber.receive_events else 'No',
                subscriber.source,
                subscriber.created_at.strftime('%Y-%m-%d %H:%M')
            ])
            
        self.message_user(request, f"{queryset.count()} subscribers exported successfully.", messages.SUCCESS)
        return response
    export_subscribers_csv.short_description = "Export selected subscribers to CSV"
    
    def mark_as_inactive(self, request, queryset):
        """Mark selected subscribers as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} subscribers marked as inactive.", messages.SUCCESS)
    mark_as_inactive.short_description = "Mark selected subscribers as inactive"
    
    def mark_as_active(self, request, queryset):
        """Mark selected subscribers as active"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} subscribers marked as active.", messages.SUCCESS)
    mark_as_active.short_description = "Mark selected subscribers as active"
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/send-test/',
                self.admin_site.admin_view(self.send_test_email),
                name='send_test_email',
            ),
            path(
                '<path:object_id>/toggle/',
                self.admin_site.admin_view(self.toggle_subscription),
                name='toggle_subscription',
            ),
            path(
                'newsletter-stats/',
                self.admin_site.admin_view(self.newsletter_stats_view),
                name='newsletter_stats',
            ),
        ]
        return custom_urls + urls
    
    def send_test_email(self, request, object_id):
        """Send a test email to the subscriber"""
        from .utils import send_welcome_email
        
        subscription = self.get_object(request, object_id)
        if subscription:
            success = send_welcome_email(subscription.email, subscription.name)
            if success:
                self.message_user(request, f"Test email sent to {subscription.email}.", messages.SUCCESS)
            else:
                self.message_user(request, f"Failed to send test email to {subscription.email}.", messages.ERROR)
        return redirect('admin:newsletter_newslettersubscription_change', object_id)
    
    def toggle_subscription(self, request, object_id):
        """Toggle the active status of a subscription"""
        subscription = self.get_object(request, object_id)
        if subscription:
            subscription.is_active = not subscription.is_active
            subscription.save()
            status = "activated" if subscription.is_active else "deactivated"
            self.message_user(request, f"Subscription for {subscription.email} {status} successfully.", messages.SUCCESS)
        return redirect('admin:newsletter_newslettersubscription_changelist')
    
    def newsletter_stats_view(self, request):
        """Display newsletter statistics"""
        from django.db.models import Count, Q
        from django.shortcuts import render
        
        context = {
            'title': 'Newsletter Statistics',
            'app_label': 'newsletter',
            'opts': NewsletterSubscription._meta,
            'has_change_permission': self.has_change_permission(request),
            'total_subscribers': NewsletterSubscription.objects.count(),
            'active_subscribers': NewsletterSubscription.objects.filter(is_active=True).count(),
            'today_subscribers': NewsletterSubscription.objects.filter(created_at__date=timezone.now().date()).count(),
            'preference_stats': {
                'updates': NewsletterSubscription.objects.filter(receive_updates=True, is_active=True).count(),
                'lab_news': NewsletterSubscription.objects.filter(receive_lab_news=True, is_active=True).count(),
                'tips': NewsletterSubscription.objects.filter(receive_tips=True, is_active=True).count(),
                'events': NewsletterSubscription.objects.filter(receive_events=True, is_active=True).count(),
            },
            'source_stats': NewsletterSubscription.objects.filter(is_active=True).values('source').annotate(count=Count('id')),
        }
        
        return render(request, 'admin/newsletter/newslettersubscription/stats.html', context)