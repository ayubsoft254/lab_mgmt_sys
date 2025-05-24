from django.contrib import admin
from .models import NewsletterSubscription, EmailTemplate, EmailCampaign, EmailDelivery
from django.utils.html import format_html
from django.urls import reverse, path
from django import forms
from django.contrib import messages
import csv
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from django.contrib.admin.widgets import AdminDateWidget
from django.db.models import Q, Count
import json

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

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'created_at', 'updated_at')
    search_fields = ('name', 'subject')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'subject', 'created_at', 'updated_at')
        }),
        ('Content', {
            'fields': ('html_content', 'text_content')
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:template_id>/preview/',
                self.admin_site.admin_view(self.preview_template),
                name='preview_template',
            ),
        ]
        return custom_urls + urls
        
    def preview_template(self, request, template_id):
        template = get_object_or_404(EmailTemplate, id=template_id)
        return render(request, 'admin/newsletter/emailtemplate/preview.html', {
            'template': template,
        })

class EmailCampaignAdminForm(forms.ModelForm):
    scheduled_time = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(date_attrs={'type': 'date'}, time_attrs={'type': 'time'}),
        required=False
    )
    
    class Meta:
        model = EmailCampaign
        exclude = ['status', 'started_at', 'completed_at', 'total_recipients', 'sent_count', 'open_count', 'click_count']

@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    form = EmailCampaignAdminForm
    list_display = ('name', 'subject', 'recipient_type', 'status', 'recipient_count', 'campaign_progress', 'created_at')
    list_filter = ('status', 'recipient_type', 'created_at')
    search_fields = ('name', 'subject')
    readonly_fields = ('created_at', 'started_at', 'completed_at', 'total_recipients', 'sent_count', 'open_count', 'click_count')
    actions = ['send_campaign_now']
    
    def get_fieldsets(self, request, obj=None):
        if obj:  # Editing existing object
            return (
                ('Campaign Information', {
                    'fields': ('name', 'subject', 'recipient_type', 'created_by', 'created_at')
                }),
                ('Content', {
                    'fields': ('template', 'custom_html_content', 'custom_text_content')
                }),
                ('Schedule', {
                    'fields': ('scheduled_time',)
                }),
                ('Status & Statistics', {
                    'fields': ('status', 'started_at', 'completed_at', 'total_recipients', 'sent_count', 'open_count', 'click_count')
                }),
            )
        return (  # Creating new object
            ('Campaign Information', {
                'fields': ('name', 'subject', 'recipient_type')
            }),
            ('Content', {
                'fields': ('template', 'custom_html_content', 'custom_text_content')
            }),
            ('Schedule', {
                'fields': ('scheduled_time',)
            }),
        )
        
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def recipient_count(self, obj):
        if obj.status == 'draft':
            return obj.get_recipients_queryset().count()
        return obj.total_recipients
    recipient_count.short_description = 'Recipients'
    
    def campaign_progress(self, obj):
        if obj.status in ['draft', 'scheduled']:
            return '-'
        return f"{obj.progress_percentage}% ({obj.sent_count}/{obj.total_recipients})"
    campaign_progress.short_description = 'Progress'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:campaign_id>/send/',
                self.admin_site.admin_view(self.send_campaign),
                name='send_campaign',
            ),
            path(
                '<int:campaign_id>/preview/',
                self.admin_site.admin_view(self.preview_campaign),
                name='preview_campaign',
            ),
            path(
                '<int:campaign_id>/status/',
                self.admin_site.admin_view(self.campaign_status),
                name='campaign_status',
            ),
        ]
        return custom_urls + urls
        
    def send_campaign_now(self, request, queryset):
        """Admin action to send selected campaigns immediately"""
        for campaign in queryset:
            if campaign.status in ['draft', 'scheduled']:
                self.process_campaign(campaign)
                self.message_user(request, f"Campaign '{campaign.name}' has been queued for sending.")
            else:
                self.message_user(
                    request, 
                    f"Cannot send campaign '{campaign.name}' because it's already {campaign.get_status_display()}.",
                    level='warning'
                )
    send_campaign_now.short_description = "Send selected campaigns now"
        
    def send_campaign(self, request, campaign_id):
        """View for sending a campaign manually"""
        campaign = get_object_or_404(EmailCampaign, id=campaign_id)
        if campaign.status in ['draft', 'scheduled']:
            self.process_campaign(campaign)
            messages.success(request, f"Campaign '{campaign.name}' has been queued for sending.")
        else:
            messages.warning(request, f"Cannot send campaign because it's already {campaign.get_status_display()}.")
        
        return redirect('admin:newsletter_emailcampaign_change', campaign_id)
        
    def preview_campaign(self, request, campaign_id):
        """View for previewing a campaign"""
        campaign = get_object_or_404(EmailCampaign, id=campaign_id)
        
        return render(request, 'admin/newsletter/emailcampaign/preview.html', {
            'campaign': campaign,
        })
        
    def campaign_status(self, request, campaign_id):
        """API endpoint to check campaign status for AJAX polling"""
        campaign = get_object_or_404(EmailCampaign, id=campaign_id)
        
        data = {
            'status': campaign.status,
            'progress': campaign.progress_percentage,
            'sent_count': campaign.sent_count,
            'total_recipients': campaign.total_recipients,
        }
        
        return JsonResponse(data)
    
    def process_campaign(self, campaign):
        """Start processing a campaign in the background"""
        from .tasks import process_email_campaign
        
        # Update campaign status
        campaign.status = 'sending'
        campaign.started_at = timezone.now()
        
        # Get recipients
        recipients = campaign.get_recipients_queryset()
        campaign.total_recipients = recipients.count()
        campaign.save()
        
        # Create EmailDelivery records for each recipient
        batch_size = 1000  # Process in chunks to avoid memory issues
        recipient_ids = list(recipients.values_list('id', flat=True))
        
        for i in range(0, len(recipient_ids), batch_size):
            batch = recipient_ids[i:i+batch_size]
            batch_users = User.objects.filter(id__in=batch)
            
            deliveries = []
            for user in batch_users:
                deliveries.append(EmailDelivery(
                    campaign=campaign,
                    recipient=user,
                    email_address=user.email,
                    status='pending'
                ))
            
            # Bulk create delivery records
            EmailDelivery.objects.bulk_create(deliveries)
        
        # Queue task to process the campaign
        process_email_campaign.delay(campaign.id)

@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    list_display = ('email_address', 'status', 'campaign', 'sent_at', 'opened_at')
    list_filter = ('status', 'sent_at', 'opened_at')
    search_fields = ('email_address', 'recipient__username', 'recipient__first_name', 'recipient__last_name')
    readonly_fields = ('campaign', 'recipient', 'email_address', 'status', 'tracking_id', 
                      'sent_at', 'opened_at', 'clicked_at', 'error_message')
    
    def has_add_permission(self, request):
        return False