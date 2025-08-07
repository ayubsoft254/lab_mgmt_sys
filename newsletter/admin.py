from django.contrib import admin
from .models import NewsletterSubscription, EmailTemplate, EmailCampaign, EmailDelivery, CsvRecipient
from .forms import CsvEmailCampaignForm, EmailCampaignAdminForm
from django.utils.html import format_html
from django.urls import reverse, path
from django import forms
from django.contrib import messages
import csv
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.template import Template, Context
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

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
    
    def get_urls(self):
        """Add custom URLs for admin actions"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:object_id>/send-test-email/',
                self.admin_site.admin_view(self.send_test_email),
                name='send_test_email',
            ),
            path(
                '<int:object_id>/toggle-subscription/',
                self.admin_site.admin_view(self.toggle_subscription),
                name='toggle_subscription',
            ),
            path(
                'stats/',
                self.admin_site.admin_view(self.newsletter_stats_view),
                name='newsletter_stats',
            ),
        ]
        return custom_urls + urls
    
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
            
        self.message_user(request, "{} subscribers exported successfully.".format(queryset.count()), messages.SUCCESS)
        return response
    export_subscribers_csv.short_description = "Export selected subscribers to CSV"
    
    def mark_as_inactive(self, request, queryset):
        """Mark selected subscribers as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(request, "{} subscribers marked as inactive.".format(updated), messages.SUCCESS)
    mark_as_inactive.short_description = "Mark selected subscribers as inactive"
    
    def mark_as_active(self, request, queryset):
        """Mark selected subscribers as active"""
        updated = queryset.update(is_active=True)
        self.message_user(request, "{} subscribers marked as active.".format(updated), messages.SUCCESS)
    mark_as_active.short_description = "Mark selected subscribers as active"
    
    def send_test_email(self, request, object_id):
        """Send a test email to the subscriber"""
        from .utils import send_welcome_email
        
        subscription = self.get_object(request, object_id)
        if subscription:
            success = send_welcome_email(subscription.email, subscription.name)
            if success:
                self.message_user(request, "Test email sent to {}.".format(subscription.email), messages.SUCCESS)
            else:
                self.message_user(request, "Failed to send test email to {}.".format(subscription.email), messages.ERROR)
        return redirect('admin:newsletter_newslettersubscription_change', object_id)
    
    def toggle_subscription(self, request, object_id):
        """Toggle the active status of a subscription"""
        subscription = self.get_object(request, object_id)
        if subscription:
            subscription.is_active = not subscription.is_active
            subscription.save()
            status = "activated" if subscription.is_active else "deactivated"
            self.message_user(request, "Subscription for {} {} successfully.".format(
                subscription.email, status), messages.SUCCESS)
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

@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    form = EmailCampaignAdminForm
    list_display = ('name', 'subject', 'recipient_type', 'status', 'recipient_count', 'campaign_progress', 'created_at')
    list_filter = ('status', 'recipient_type', 'created_at')
    search_fields = ('name', 'subject')
    readonly_fields = ('created_at', 'started_at', 'completed_at', 'total_recipients', 'sent_count', 'open_count', 'click_count')
    actions = ['send_campaign_now']
    
    def recipient_count(self, obj):
        """Display the number of recipients for this campaign"""
        if obj.recipient_type == 'csv_upload':
            return obj.csv_recipients.count()
        else:
            return obj.total_recipients
    recipient_count.short_description = 'Recipients'
    
    def campaign_progress(self, obj):
        """Display campaign progress as a percentage"""
        if obj.total_recipients == 0:
            return "0%"
        progress = (obj.sent_count / obj.total_recipients) * 100
        color = "green" if progress == 100 else "orange" if progress > 0 else "red"
        progress_text = "{:.1f}".format(progress)
        return format_html(
            '<span style="color: {};">{}% ({}/{})</span>',
            color, progress_text, obj.sent_count, obj.total_recipients
        )
    campaign_progress.short_description = 'Progress'
    
    def get_fieldsets(self, request, obj=None):
        if obj:
            fieldsets = [
                ('Campaign Information', {
                    'fields': ('name', 'subject', 'recipient_type', 'sender_email', 'created_by', 'created_at')
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
            ]
            
            if obj.recipient_type == 'csv_upload' and obj.csv_file:
                fieldsets.insert(2, ('CSV Upload', {
                    'fields': ('csv_file',),
                    'description': 'CSV file uploaded: {}'.format(obj.csv_file.name)
                }))
            
            return fieldsets
        
        return (
            ('Campaign Information', {
                'fields': ('name', 'subject', 'recipient_type', 'sender_email_choice', 'custom_sender_email')
            }),
            ('Content', {
                'fields': ('template', 'custom_html_content', 'custom_text_content')
            }),
            ('CSV Upload', {
                'fields': ('csv_file',),
                'classes': ('collapse',),
                'description': 'Only required when recipient type is "CSV Upload Recipients"'
            }),
            ('Schedule', {
                'fields': ('scheduled_time',)
            }),
        )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'csv-campaign/',
                self.admin_site.admin_view(self.csv_campaign_view),
                name='csv_campaign',
            ),
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
    
    def changelist_view(self, request, extra_context=None):
        """Add custom buttons to the changelist view"""
        extra_context = extra_context or {}
        extra_context['csv_campaign_url'] = reverse('admin:csv_campaign')
        return super().changelist_view(request, extra_context=extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add custom buttons to the change view"""
        extra_context = extra_context or {}
        if object_id:
            extra_context.update({
                'preview_url': reverse('admin:preview_campaign', args=[object_id]),
                'send_url': reverse('admin:send_campaign', args=[object_id]),
                'status_url': reverse('admin:campaign_status', args=[object_id]),
            })
        return super().change_view(request, object_id, form_url, extra_context)
    
    def csv_campaign_view(self, request):
        """View for creating CSV-based email campaigns with improved error handling"""
        if request.method == 'POST':
            form = CsvEmailCampaignForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        campaign = form.save(commit=False)
                        campaign.created_by = request.user
                        campaign.recipient_type = 'csv_upload'
                        campaign.save()
                        
                        # Process CSV file
                        success, message = self.process_csv_file(campaign, form.cleaned_data['csv_file'])
                        
                        if success:
                            messages.success(request, f"CSV campaign '{campaign.name}' created successfully! {message}")
                            return redirect('admin:newsletter_emailcampaign_change', campaign.id)
                        else:
                            campaign.delete()
                            messages.error(request, f"Failed to process CSV file: {message}")
                except Exception as e:
                    messages.error(request, f"Error creating campaign: {str(e)}")
        else:
            form = CsvEmailCampaignForm()
        
        return render(request, 'admin/newsletter/emailcampaign/csv_campaign.html', {
            'form': form,
            'title': 'Create CSV Email Campaign',
            'opts': EmailCampaign._meta,
        })
    
    def send_campaign(self, request, campaign_id):
        """Send a campaign immediately with better error handling"""
        campaign = get_object_or_404(EmailCampaign, id=campaign_id)
        
        if campaign.status not in ['draft', 'scheduled']:
            messages.error(request, f"Campaign '{campaign.name}' cannot be sent. Current status: {campaign.get_status_display()}")
            return redirect('admin:newsletter_emailcampaign_change', campaign_id)
        
        try:
            self.process_campaign(campaign)
            messages.success(request, f"Campaign '{campaign.name}' has been queued for sending!")
        except Exception as e:
            messages.error(request, f"Failed to queue campaign: {str(e)}")
        
        return redirect('admin:newsletter_emailcampaign_change', campaign_id)
    
    def preview_campaign(self, request, campaign_id):
        """Preview campaign content with sample context"""
        campaign = get_object_or_404(EmailCampaign, id=campaign_id)
        
        # Create sample context for preview
        if campaign.recipient_type == 'csv_upload':
            csv_recipient = campaign.csv_recipients.first()
            context = {
                'email': csv_recipient.email if csv_recipient else 'example@example.com',
                'name': csv_recipient.data.get('name', 'John Doe') if csv_recipient else 'John Doe',
                **(csv_recipient.data if csv_recipient else {})
            }
        else:
            context = {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@example.com',
            }
        
        try:
            # Render content with context
            subject = Template(campaign.subject).render(Context(context)) if campaign.subject else "No subject"
            html_content = Template(campaign.html_content).render(Context(context)) if campaign.html_content else "No HTML content"
            text_content = Template(campaign.text_content).render(Context(context)) if campaign.text_content else "No text content"
                
        except Exception as e:
            messages.error(request, f"Error rendering template: {str(e)}")
            return redirect('admin:newsletter_emailcampaign_change', campaign_id)
        
        return render(request, 'admin/newsletter/emailcampaign/preview.html', {
            'campaign': campaign,
            'subject': subject,
            'html_content': html_content,
            'text_content': text_content,
            'context': context,
            'title': f'Preview: {campaign.name}',
            'opts': EmailCampaign._meta,
        })
    
    def campaign_status(self, request, campaign_id):
        """View campaign status and statistics"""
        campaign = get_object_or_404(EmailCampaign, id=campaign_id)
        
        context = {
            'campaign': campaign,
            'title': f'Status: {campaign.name}',
            'opts': EmailCampaign._meta,
        }
        
        if campaign.recipient_type == 'csv_upload':
            context['csv_recipients'] = campaign.csv_recipients.all()[:10]
            context['total_csv_recipients'] = campaign.csv_recipients.count()
        else:
            context['deliveries'] = EmailDelivery.objects.filter(campaign=campaign)[:10]
            context['delivery_stats'] = {
                'pending': EmailDelivery.objects.filter(campaign=campaign, status='pending').count(),
                'sent': EmailDelivery.objects.filter(campaign=campaign, status='sent').count(),
                'opened': EmailDelivery.objects.filter(campaign=campaign, status='opened').count(),
                'clicked': EmailDelivery.objects.filter(campaign=campaign, status='clicked').count(),
                'failed': EmailDelivery.objects.filter(campaign=campaign, status='failed').count(),
            }
        
        return render(request, 'admin/newsletter/emailcampaign/status.html', context)
    
    def send_campaign_now(self, request, queryset):
        """Admin action to send selected campaigns immediately"""
        sent_count = 0
        for campaign in queryset:
            if campaign.status in ['draft', 'scheduled']:
                try:
                    self.process_campaign(campaign)
                    sent_count += 1
                    messages.success(request, f"Campaign '{campaign.name}' queued for sending")
                except Exception as e:
                    messages.error(request, f"Failed to queue campaign '{campaign.name}': {str(e)}")
            else:
                messages.warning(request, f"Campaign '{campaign.name}' could not be sent (status: {campaign.get_status_display()})")
        
        if sent_count > 0:
            messages.success(request, f"{sent_count} campaign(s) queued for sending!")
    send_campaign_now.short_description = "Send selected campaigns now"
    
    def process_csv_file(self, campaign, csv_file):
        """Process uploaded CSV file and create CsvRecipient records with validation"""
        import io
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        csv_file.seek(0)
        content = csv_file.read().decode('utf-8')
        
        try:
            reader = csv.DictReader(io.StringIO(content))
            if 'email' not in reader.fieldnames:
                raise ValueError("CSV file must contain an 'email' column")
                
            recipients = []
            seen_emails = set()
            row_num = 0
            valid_count = 0
            
            for row_num, row in enumerate(reader, 1):
                email = row.get('email', '').strip().lower()
                if not email:
                    continue
                    
                try:
                    validate_email(email)
                except ValidationError:
                    continue
                
                if email in seen_emails:
                    continue
                seen_emails.add(email)
                
                row_data = {k: v.strip() for k, v in row.items() if k != 'email' and v.strip()}
                
                recipients.append(CsvRecipient(
                    campaign=campaign,
                    email=email,
                    data=row_data
                ))
                
                valid_count += 1
                
                # Batch create every 10 records
                if len(recipients) >= 10:
                    CsvRecipient.objects.bulk_create(recipients)
                    recipients = []
            
            # Create remaining recipients
            if recipients:
                CsvRecipient.objects.bulk_create(recipients)
            
            campaign.total_recipients = valid_count
            campaign.save()
            
            return True, f"Processed {valid_count} valid recipients from {row_num} rows"
            
        except Exception as e:
            return False, f"Error processing CSV at row {row_num}: {str(e)}"
    
    def process_campaign(self, campaign):
        """Start processing a campaign in the background with improved CSV handling"""
        from .tasks import process_email_campaign, process_csv_campaign_batch
        
        campaign.status = 'sending'
        campaign.started_at = timezone.now()
        
        try:
            if campaign.recipient_type == 'csv_upload':
                if not campaign.csv_recipients.exists():
                    raise ValueError("No valid CSV recipients found")
                
                campaign.total_recipients = campaign.csv_recipients.count()
                campaign.save()
                
                # Use batch processing for large campaigns
                if campaign.total_recipients > 10:
                    process_csv_campaign_batch.delay(campaign.id)
                else:
                    process_email_campaign.delay(campaign.id)
            else:
                recipients = campaign.get_recipients_queryset()
                campaign.total_recipients = recipients.count()
                
                # Create EmailDelivery records in batches
                batch_size = 10
                for i in range(0, campaign.total_recipients, batch_size):
                    batch = recipients[i:i+batch_size]
                    deliveries = [
                        EmailDelivery(
                            campaign=campaign,
                            recipient=user,
                            email_address=user.email,
                            status='pending'
                        )
                        for user in batch
                    ]
                    EmailDelivery.objects.bulk_create(deliveries)
                
                campaign.save()
                process_email_campaign.delay(campaign.id)
                
        except Exception as e:
            campaign.status = 'failed'
            campaign.save()
            raise e

@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    list_display = ('email_address', 'status', 'campaign', 'sent_at', 'opened_at')
    list_filter = ('status', 'sent_at', 'opened_at')
    search_fields = ('email_address', 'recipient__username', 'recipient__first_name', 'recipient__last_name')
    readonly_fields = ('campaign', 'recipient', 'email_address', 'status', 'tracking_id', 
                      'sent_at', 'opened_at', 'clicked_at', 'error_message')
    
    def has_add_permission(self, request):
        return False

@admin.register(CsvRecipient)
class CsvRecipientAdmin(admin.ModelAdmin):
    list_display = ('email', 'campaign', 'data_preview', 'created_at')
    list_filter = ('campaign', 'created_at')
    search_fields = ('email', 'campaign__name')
    readonly_fields = ('campaign', 'email', 'data', 'created_at')
    
    def data_preview(self, obj):
        """Show a preview of the data"""
        if obj.data:
            preview = ', '.join([f"{k}: {v}" for k, v in list(obj.data.items())[:3]])
            if len(obj.data) > 3:
                preview += "..."
            return preview
        return "No data"
    data_preview.short_description = 'Data Preview'
    
    def has_add_permission(self, request):
        return False

# Create a reference to the stats view for importing in urls.py
admin_stats_view = NewsletterSubscriptionAdmin.newsletter_stats_view