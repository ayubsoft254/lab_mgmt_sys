from django.contrib import admin
from .models import SystemEvent

# Register your models here.
@admin.register(SystemEvent)
class SystemEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'ip_address', 'timestamp')
    list_filter = ('event_type', 'user')
    search_fields = ('user__username', 'ip_address')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)