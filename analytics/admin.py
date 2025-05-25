from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import timedelta
from .models import SystemEvent


@admin.register(SystemEvent)
class SystemEventAdmin(admin.ModelAdmin):
    """Enhanced admin interface for SystemEvent model"""
    
    list_display = [
        'id', 
        'event_type_badge', 
        'user_link', 
        'severity_badge', 
        'timestamp_formatted', 
        'resolved_status',
        'details_preview'
    ]
    
    list_filter = [
        'event_type',
        'severity', 
        'resolved',
        'timestamp',
        ('user', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'details',
        'event_type',
        'ip_address',
    ]
    
    readonly_fields = [
        'id',
        'timestamp',
        'created_at_formatted',
        'time_since_created',
        'resolution_info',
    ]
    
    fieldsets = (
        ('Event Information', {
            'fields': ('id', 'event_type', 'severity', 'timestamp', 'created_at_formatted', 'time_since_created')
        }),
        ('User Information', {
            'fields': ('user', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Event Details', {
            'fields': ('details', 'metadata'),
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolved_by', 'resolved_at', 'resolution_notes', 'resolution_info'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    list_per_page = 50
    list_max_show_all = 200
    
    actions = [
        'mark_as_resolved',
        'mark_as_unresolved',
        'export_selected_events',
        'bulk_delete_old_events',
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'user', 'resolved_by'
        ).prefetch_related()
    
    def event_type_badge(self, obj):
        """Display event type with colored badge"""
        color_map = {
            'LOGIN': 'success',
            'LOGOUT': 'info',
            'LOGIN_FAILED': 'danger',
            'PASSWORD_CHANGE': 'warning',
            'PASSWORD_RESET': 'warning',
            'PROFILE_UPDATE': 'info',
            'PERMISSION_DENIED': 'danger',
            'UNAUTHORIZED_ACCESS': 'danger',
            'DATA_EXPORT': 'warning',
            'DATA_IMPORT': 'warning',
            'SYSTEM_ERROR': 'danger',
            'API_ACCESS': 'info',
            'BOOKING_CREATED': 'primary',
            'BOOKING_CANCELLED': 'secondary',
            'LAB_ACCESS': 'success',
        }
        
        color = color_map.get(obj.event_type, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_event_type_display()
        )
    event_type_badge.short_description = 'Event Type'
    event_type_badge.admin_order_field = 'event_type'
    
    def severity_badge(self, obj):
        """Display severity with colored badge"""
        color_map = {
            'CRITICAL': 'danger',
            'HIGH': 'warning',
            'MEDIUM': 'info',
            'LOW': 'success',
        }
        
        color = color_map.get(obj.severity, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'
    severity_badge.admin_order_field = 'severity'
    
    def user_link(self, obj):
        """Create clickable link to user"""
        if obj.user:
            # Use the correct app_label and model_name from the user object itself
            app_label = obj.user._meta.app_label
            model_name = obj.user._meta.model_name
            url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.user.pk])
            return format_html(
                '<a href="{}" title="View user details">{}</a>',
                url,
                obj.user.username
            )
        return format_html('<em>Anonymous</em>')
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def timestamp_formatted(self, obj):
        """Format timestamp with relative time"""
        return format_html(
            '<span title="{}">{}</span>',
            obj.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
            obj.timestamp.strftime('%b %d, %Y %H:%M')
        )
    timestamp_formatted.short_description = 'Date/Time'
    timestamp_formatted.admin_order_field = 'timestamp'
    
    def resolved_status(self, obj):
        """Display resolution status with icon"""
        if obj.resolved:
            return format_html(
                '<span class="badge badge-success" title="Resolved by {} on {}">✓ Resolved</span>',
                obj.resolved_by.username if obj.resolved_by else 'System',
                obj.resolved_at.strftime('%Y-%m-%d %H:%M') if obj.resolved_at else 'Unknown'
            )
        else:
            return format_html('<span class="badge badge-warning">⏳ Open</span>')
    resolved_status.short_description = 'Status'
    resolved_status.admin_order_field = 'resolved'
    
    def details_preview(self, obj):
        """Show truncated details"""
        if obj.details:
            import json
            
            # Pretty format the JSON for the tooltip
            full_details = json.dumps(obj.details, indent=2)
            
            # Create a simplified preview
            if isinstance(obj.details, dict):
                # For dictionaries, show key count
                keys = list(obj.details.keys())[:3]  # Get first 3 keys
                preview = f"{len(obj.details)} keys: {', '.join(keys)}"
                if len(obj.details) > 3:
                    preview += ", ..."
            elif isinstance(obj.details, list):
                # For lists, show item count
                preview = f"{len(obj.details)} items"
            else:
                # For other types, convert to string
                preview = str(obj.details)[:100] + ('...' if len(str(obj.details)) > 100 else '')
                
            return format_html('<span title="{}">{}</span>', full_details.replace('"', '&quot;'), preview)
        return format_html('<em>No details</em>')
    details_preview.short_description = 'Details'
    
    def created_at_formatted(self, obj):
        """Format creation timestamp"""
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
    created_at_formatted.short_description = 'Created At'
    
    def time_since_created(self, obj):
        """Show time elapsed since creation"""
        now = timezone.now()
        diff = now - obj.timestamp
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    time_since_created.short_description = 'Time Elapsed'
    
    def resolution_info(self, obj):
        """Display resolution information"""
        if obj.resolved:
            info = f"Resolved by: {obj.resolved_by.username if obj.resolved_by else 'System'}<br>"
            info += f"Resolved at: {obj.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if obj.resolved_at else 'Unknown'}<br>"
            if obj.resolution_notes:
                info += f"Notes: {obj.resolution_notes}"
            return mark_safe(info)
        return "Not resolved"
    resolution_info.short_description = 'Resolution Details'
    
    # Custom Actions
    def mark_as_resolved(self, request, queryset):
        """Mark selected events as resolved"""
        updated = queryset.filter(resolved=False).update(
            resolved=True,
            resolved_by=request.user,
            resolved_at=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} events marked as resolved.'
        )
    mark_as_resolved.short_description = "Mark selected events as resolved"
    
    def mark_as_unresolved(self, request, queryset):
        """Mark selected events as unresolved"""
        updated = queryset.filter(resolved=True).update(
            resolved=False,
            resolved_by=None,
            resolved_at=None,
            resolution_notes=''
        )
        self.message_user(
            request,
            f'{updated} events marked as unresolved.'
        )
    mark_as_unresolved.short_description = "Mark selected events as unresolved"
    
    def export_selected_events(self, request, queryset):
        """Export selected events to CSV"""
        import csv
        import json
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="system_events.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Event Type', 'User', 'Severity', 'Timestamp', 
            'Resolved', 'IP Address', 'Details'
        ])
        
        for event in queryset:
            # Convert details to JSON string if it's not already a string
            details_str = json.dumps(event.details) if event.details else ''
            
            writer.writerow([
                event.id,
                event.get_event_type_display(),
                event.user.username if event.user else 'Anonymous',
                event.get_severity_display(),
                event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'Yes' if event.resolved else 'No',
                event.ip_address or '',
                details_str
            ])
        
        return response
    export_selected_events.short_description = "Export selected events to CSV"
    
    def bulk_delete_old_events(self, request, queryset):
        """Delete events older than 1 year that are resolved"""
        one_year_ago = timezone.now() - timedelta(days=365)
        old_resolved_events = queryset.filter(
            timestamp__lt=one_year_ago,
            resolved=True
        )
        count = old_resolved_events.count()
        old_resolved_events.delete()
        
        self.message_user(
            request,
            f'{count} old resolved events deleted.'
        )
    bulk_delete_old_events.short_description = "Delete old resolved events (1+ year)"
    
    def get_list_display_links(self, request, list_display):
        """Make ID and event type clickable"""
        return ('id', 'event_type_badge')
    
    def has_add_permission(self, request):
        """Disable manual addition of events"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only allow deletion for superusers"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Allow changing resolution status and notes"""
        return request.user.has_perm('system_events.change_systemevent')
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/custom_admin.js',)


# Custom admin site configuration (optional)
class SystemEventsAdminSite(admin.AdminSite):
    """Custom admin site for system events"""
    site_header = 'System Events Administration'
    site_title = 'System Events Admin'
    index_title = 'System Events Dashboard'
    
    def index(self, request, extra_context=None):
        """Add custom context to admin index"""
        extra_context = extra_context or {}
        
        # Add statistics
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        
        stats = {
            'total_events': SystemEvent.objects.count(),
            'today_events': SystemEvent.objects.filter(timestamp__gte=today).count(),
            'week_events': SystemEvent.objects.filter(timestamp__gte=week_ago).count(),
            'unresolved_events': SystemEvent.objects.filter(resolved=False).count(),
            'critical_events': SystemEvent.objects.filter(
                severity='CRITICAL', 
                resolved=False
            ).count(),
        }
        
        extra_context['system_stats'] = stats
        return super().index(request, extra_context)