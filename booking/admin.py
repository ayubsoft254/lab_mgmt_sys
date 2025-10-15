from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, Lab, Computer, ComputerBooking, LabSession, Notification, RecurringSession, StudentRating, LabAdministrator, Announcement

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_student', 
                    'is_lecturer', 'is_admin', 'is_super_admin')
    list_filter = ('is_student', 'is_lecturer', 'is_admin', 'is_super_admin', 'school')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('salutation', 'first_name', 'last_name', 'email')}),
        ('TTU information', {'fields': ('school', 'course')}),
        ('Roles', {'fields': ('is_student', 'is_lecturer')}),
        ('Admin Status', {'fields': ('is_admin', 'is_super_admin', 'managed_labs')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'salutation', 'first_name', 'last_name', 
                       'school', 'course', 'is_student', 'is_lecturer', 'is_admin')}
        ),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'course')
    filter_horizontal = ('managed_labs', 'groups', 'user_permissions')

@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'capacity')
    search_fields = ('name', 'location')

@admin.register(Computer)
class ComputerAdmin(admin.ModelAdmin):
    list_display = ('lab', 'computer_number', 'status')
    list_filter = ('lab', 'status')
    search_fields = ('lab__name', 'computer_number')

@admin.register(ComputerBooking)
class ComputerBookingAdmin(admin.ModelAdmin):
    list_display = ('computer', 'student', 'start_time', 'end_time', 'is_approved', 'is_cancelled')
    list_filter = ('is_approved', 'is_cancelled')
    search_fields = ('computer__lab__name', 'student__username', 'booking_code')

@admin.register(LabSession)
class LabSessionAdmin(admin.ModelAdmin):
    list_display = ('lab', 'lecturer', 'title', 'start_time', 'end_time', 'is_approved')
    list_filter = ('is_approved',)
    search_fields = ('lab__name', 'lecturer__username', 'title')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__username', 'message')

@admin.register(RecurringSession)
class RecurringSessionAdmin(admin.ModelAdmin):
    list_display = ('lab', 'lecturer', 'title', 'recurrence_type', 'start_time', 'end_time')
    search_fields = ('lab__name', 'lecturer__username', 'title')

@admin.register(LabAdministrator)
class LabAdministratorAdmin(admin.ModelAdmin):
    list_display = ('admin', 'lab', 'date_assigned')
    list_filter = ('lab', 'date_assigned')
    search_fields = ('admin__username', 'lab__name')
    autocomplete_fields = ['admin', 'lab']

@admin.register(StudentRating)
class StudentRatingAdmin(admin.ModelAdmin):
    list_display = ('student', 'rated_by', 'score', 'created_at')
    list_filter = ('score', 'created_at')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'comment')
    autocomplete_fields = ['student', 'rated_by', 'session', 'booking']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    """Admin interface for managing system-wide announcements"""
    list_display = ('title', 'priority_display', 'status_display', 'recipient_count', 'created_by', 'published_at')
    list_filter = ('status', 'priority', 'created_at', 'send_email')
    search_fields = ('title', 'message', 'description')
    readonly_fields = ('created_at', 'updated_at', 'published_at', 'notifications_sent', 'emails_sent', 'recipient_preview')
    filter_horizontal = ('target_users',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'message', 'description', 'priority', 'status')
        }),
        ('Recipients', {
            'fields': ('target_users', 'target_students', 'target_lecturers', 'target_admins', 'recipient_preview'),
            'description': 'Choose specific users or select user types. Leave users empty to use type selections.'
        }),
        ('Delivery Options', {
            'fields': ('send_email', 'in_app_only')
        }),
        ('Scheduling', {
            'fields': ('scheduled_for', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at', 'published_at', 'notifications_sent', 'emails_sent'),
            'classes': ('collapse',)
        }),
    )
    
    def priority_display(self, obj):
        """Display priority with color-coding"""
        colors = {
            'low': '#3498db',
            'medium': '#f39c12',
            'high': '#e74c3c',
            'urgent': '#8e44ad',
        }
        color = colors.get(obj.priority, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_display.short_description = 'Priority'
    
    def status_display(self, obj):
        """Display status with color-coding"""
        colors = {
            'draft': '#95a5a6',
            'scheduled': '#3498db',
            'active': '#27ae60',
            'archived': '#7f8c8d',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def recipient_count(self, obj):
        """Display count of recipients"""
        count = obj.get_recipient_count()
        return format_html(
            '<span style="background-color: #2c6e49; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{} user(s)</span>',
            count
        )
    recipient_count.short_description = 'Recipients'
    
    def recipient_preview(self, obj):
        """Show preview of who will receive this announcement"""
        if not obj.pk:
            return 'Not saved yet'
        
        recipients = []
        if obj.target_users.exists():
            recipients.append(f"<strong>Specific Users:</strong> {obj.target_users.count()} selected")
        else:
            if obj.target_students:
                students = User.objects.filter(is_student=True).count()
                recipients.append(f"<strong>Students:</strong> {students}")
            if obj.target_lecturers:
                lecturers = User.objects.filter(is_lecturer=True).count()
                recipients.append(f"<strong>Lecturers:</strong> {lecturers}")
            if obj.target_admins:
                admins = User.objects.filter(is_admin=True).count()
                recipients.append(f"<strong>Admins:</strong> {admins}")
        
        total = obj.get_recipient_count()
        html = f'<div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">'
        html += '<br>'.join(recipients)
        html += f'<br><br><strong style="color: #2c6e49;">Total Recipients: {total}</strong>'
        html += '</div>'
        
        return mark_safe(html)
    recipient_preview.short_description = 'Recipient Preview'
    
    def get_readonly_fields(self, request, obj=None):
        """Make fields read-only after announcement is sent"""
        readonly = list(self.readonly_fields)
        if obj and obj.status in ['active', 'archived']:
            # Once published, make these fields read-only
            readonly.extend(['title', 'message', 'description', 'priority', 'target_users', 
                            'target_students', 'target_lecturers', 'target_admins', 'send_email', 'in_app_only'])
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Set the creator when saving"""
        if not change:  # Creating new announcement
            obj.created_by = request.user
        super().save_model(request, obj, form, change)