from django.contrib import admin
from .models import (
    SystemVersion, 
    DocumentationSection, 
    SubSection, 
    DocumentationItem, 
    ContactInfo,
    AnonymousFeedback
)

@admin.register(SystemVersion)
class SystemVersionAdmin(admin.ModelAdmin):
    list_display = ('version_number', 'version_name', 'version_type', 'release_date', 'is_current')
    list_filter = ('version_type', 'is_current')
    search_fields = ('version_number', 'version_name', 'release_notes')
    date_hierarchy = 'release_date'
    list_editable = ('is_current',)
    fieldsets = (
        ('Version Information', {
            'fields': ('version_number', 'version_name', 'version_type', 'is_current')
        }),
        ('Release Details', {
            'fields': ('release_date', 'developer', 'release_notes')
        }),
    )


class DocumentationItemInline(admin.TabularInline):
    model = DocumentationItem
    extra = 1


class SubSectionInline(admin.StackedInline):
    model = SubSection
    extra = 1
    prepopulated_fields = {'slug': ('title',)}


class ContactInfoInline(admin.TabularInline):
    model = ContactInfo
    extra = 1


@admin.register(DocumentationSection)
class DocumentationSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_visible', 'last_updated')
    list_editable = ('order', 'is_visible')
    search_fields = ('title', 'content')
    inlines = [SubSectionInline, ContactInfoInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'order', 'is_visible')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('collapse',)
        }),
    )


@admin.register(SubSection)
class SubSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'order', 'is_visible')
    list_editable = ('order', 'is_visible')
    list_filter = ('section', 'is_visible')
    search_fields = ('title', 'content')
    inlines = [DocumentationItemInline]
    fieldsets = (
        (None, {
            'fields': ('section', 'title', 'order', 'is_visible')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('title', 'email', 'phone', 'section')
    list_filter = ('section',)
    search_fields = ('title', 'email', 'phone', 'additional_info')


@admin.register(AnonymousFeedback)
class AnonymousFeedbackAdmin(admin.ModelAdmin):
    list_display = ('category', 'submission_date', 'rating', 'is_addressed')
    list_filter = ('category', 'is_addressed', 'rating', 'submission_date')
    search_fields = ('message', 'admin_notes')
    readonly_fields = ('submission_date', 'page_url')
    fieldsets = (
        ('Feedback Information', {
            'fields': ('category', 'message', 'rating', 'submission_date', 'page_url')
        }),
        ('Administrative', {
            'fields': ('is_addressed', 'admin_notes')
        }),
    )
    actions = ['mark_as_addressed', 'mark_as_unaddressed']
    
    def mark_as_addressed(self, request, queryset):
        queryset.update(is_addressed=True)
    mark_as_addressed.short_description = "Mark selected feedback as addressed"
    
    def mark_as_unaddressed(self, request, queryset):
        queryset.update(is_addressed=False)
    mark_as_unaddressed.short_description = "Mark selected feedback as unaddressed"