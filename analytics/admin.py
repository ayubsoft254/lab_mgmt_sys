from django.contrib import admin
from .models import SystemEvent

# Register your models here.
@admin.register(SystemEvent)
class SystemEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'description', 'created_at')
    list_filter = ('event_type',)
    search_fields = ('description',)
