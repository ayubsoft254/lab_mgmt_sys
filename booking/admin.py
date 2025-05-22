from django.contrib import admin
from .models import User, Lab, Computer, ComputerBooking, LabSession, Notification, RecurringSession

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_student', 'is_lecturer', 'is_admin')
    list_filter = ('is_student', 'is_lecturer', 'is_admin')
    search_fields = ('username', 'email')

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


    
