from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import ContactSubmission, Inquiry, Feedback
from .forms import AdminInquiryResponseForm


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    list_filter = ('subject', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    """Admin interface for managing user inquiries"""
    
    form = AdminInquiryResponseForm
    list_display = ('subject', 'name', 'category_display', 'status_display', 'created_at', 'action_buttons')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at', 'user', 'name', 'email', 'category', 'subject', 'message', 'formatted_inquiry_details', 'admin_responder')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Inquiry Details', {
            'fields': ('formatted_inquiry_details',)
        }),
        ('Inquiry Information', {
            'fields': ('user', 'name', 'email', 'category', 'subject', 'message'),
        }),
        ('Admin Response', {
            'fields': ('status', 'admin_response', 'admin_responder'),
            'description': 'Provide your response to the user inquiry.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields read-only for non-superusers"""
        readonly = list(self.readonly_fields)
        if obj:  # Editing an existing inquiry
            # Keep original message and details read-only
            if 'formatted_inquiry_details' not in readonly:
                readonly.append('formatted_inquiry_details')
        return readonly
    
    def category_display(self, obj):
        """Display category with color-coding"""
        colors = {
            'general': '#3498db',
            'technical': '#e74c3c',
            'booking': '#27ae60',
            'account': '#f39c12',
            'other': '#95a5a6',
        }
        color = colors.get(obj.category, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_display.short_description = 'Category'
    
    def status_display(self, obj):
        """Display status with color-coding"""
        colors = {
            'open': '#3498db',
            'in_progress': '#f39c12',
            'resolved': '#27ae60',
            'closed': '#95a5a6',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def formatted_inquiry_details(self, obj):
        """Display formatted inquiry details"""
        if not obj.pk:
            return 'Not saved yet'
        
        html = f'''
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db;">
            <p><strong>From:</strong> {obj.name} &lt;{obj.email}&gt;</p>
            <p><strong>Category:</strong> {obj.get_category_display()}</p>
            <p><strong>Subject:</strong> {obj.subject}</p>
            <hr>
            <p><strong>Message:</strong></p>
            <p style="white-space: pre-wrap; font-size: 14px;">{obj.message}</p>
            <hr>
            <p style="color: #7f8c8d; font-size: 12px;">
                <strong>Submitted:</strong> {obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
        '''
        return mark_safe(html)
    formatted_inquiry_details.short_description = 'Inquiry Details'
    
    def action_buttons(self, obj):
        """Display quick action buttons"""
        buttons = []
        if obj.status != 'resolved':
            buttons.append(
                format_html(
                    '<a class="button" href="{}?status=resolved" style="background-color: #27ae60;">Mark Resolved</a>',
                    reverse('admin:contact_inquiry_change', args=[obj.pk])
                )
            )
        buttons.append(
            format_html(
                '<a class="button" href="mailto:{}">Reply</a>',
                obj.email
            )
        )
        return format_html(' '.join(buttons))
    action_buttons.short_description = 'Actions'
    
    def save_model(self, request, obj, form, change):
        """Override save to set admin_responder"""
        if change and obj.status == 'resolved' and not obj.admin_responder:
            obj.admin_responder = request.user
            obj.resolved_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """Admin interface for managing user feedback"""
    
    list_display = ('title', 'user_display', 'category_display', 'rating_display', 'created_at', 'actionable_display')
    list_filter = ('category', 'rating', 'is_actionable', 'created_at')
    search_fields = ('title', 'name', 'email', 'message')
    readonly_fields = ('created_at', 'updated_at', 'user', 'formatted_feedback_details')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Feedback Details', {
            'fields': ('formatted_feedback_details',)
        }),
        ('Feedback Information', {
            'fields': ('user', 'name', 'email', 'category', 'title', 'message', 'rating'),
        }),
        ('Admin Notes', {
            'fields': ('admin_notes', 'is_actionable'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_display(self, obj):
        """Display user information"""
        if obj.user:
            return f"{obj.user.get_full_name()} ({obj.user.username})"
        return obj.name or 'Anonymous'
    user_display.short_description = 'User'
    
    def category_display(self, obj):
        """Display category with color-coding"""
        colors = {
            'bug': '#e74c3c',
            'feature': '#3498db',
            'ui': '#9b59b6',
            'performance': '#f39c12',
            'other': '#95a5a6',
        }
        color = colors.get(obj.category, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_display.short_description = 'Category'
    
    def rating_display(self, obj):
        """Display rating with stars"""
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        colors = {
            1: '#e74c3c',  # Red for poor
            2: '#f39c12',  # Orange for fair
            3: '#f1c40f',  # Yellow for good
            4: '#27ae60',  # Green for very good
            5: '#2ecc71',  # Bright green for excellent
        }
        color = colors.get(obj.rating, '#95a5a6')
        return format_html(
            '<span style="color: {}; font-size: 16px;">{} ({})</span>',
            color,
            stars,
            obj.get_rating_display()
        )
    rating_display.short_description = 'Rating'
    
    def actionable_display(self, obj):
        """Display if feedback requires action"""
        if obj.is_actionable:
            return format_html(
                '<span style="background-color: #e74c3c; color: white; padding: 3px 8px; border-radius: 3px;">Action Required</span>'
            )
        return format_html(
            '<span style="background-color: #95a5a6; color: white; padding: 3px 8px; border-radius: 3px;">No Action</span>'
        )
    actionable_display.short_description = 'Status'
    
    def formatted_feedback_details(self, obj):
        """Display formatted feedback details"""
        if not obj.pk:
            return 'Not saved yet'
        
        user_info = f"{obj.user.get_full_name()} ({obj.user.username})" if obj.user else f"{obj.name} &lt;{obj.email}&gt;"
        
        html = f'''
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db;">
            <p><strong>From:</strong> {user_info}</p>
            <p><strong>Category:</strong> {obj.get_category_display()}</p>
            <p><strong>Title:</strong> {obj.title}</p>
            <p><strong>Rating:</strong> {'★' * obj.rating}{'☆' * (5 - obj.rating)} ({obj.get_rating_display()})</p>
            <hr>
            <p><strong>Message:</strong></p>
            <p style="white-space: pre-wrap; font-size: 14px;">{obj.message}</p>
            <hr>
            <p style="color: #7f8c8d; font-size: 12px;">
                <strong>Submitted:</strong> {obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
        '''
        return mark_safe(html)
    formatted_feedback_details.short_description = 'Feedback Details'
