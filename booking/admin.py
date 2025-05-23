from django.contrib import admin
from .models import User, Lab, Computer, ComputerBooking, LabSession, Notification, RecurringSession
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_student', 
                    'is_lecturer', 'is_admin', 'is_super_admin')
    list_filter = ('is_student', 'is_lecturer', 'is_admin', 'is_super_admin', 'school')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('salutation', 'first_name', 'last_name', 'email')}),
        ('TTU information', {'fields': ('school', 'course')}),
        ('Roles', {'fields': ('is_student', 'is_lecturer', 'is_admin')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Admin Status', {'fields': ('is_admin', 'is_super_admin', 'managed_labs')}),
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

@admin.register(LabAdmin)
class LabAdminModelAdmin(admin.ModelAdmin):
    list_display = ('admin', 'lab', 'date_assigned')
    list_filter = ('lab', 'date_assigned')
    search_fields = ('admin__username', 'lab__name')
    autocomplete_fields = ['admin', 'lab']



