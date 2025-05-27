from django.shortcuts import render
from django.views.generic import TemplateView
from .models import SystemVersion, DocumentationSection, SubSection, DocumentationItem, ContactInfo

class DocumentationView(TemplateView):
    """
    View for displaying the system documentation from the database.
    """
    template_name = "documentation.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the current system version
        current_version = SystemVersion.objects.filter(is_current=True).first()
        if not current_version:
            # Fallback if no version is marked as current
            current_version = SystemVersion.objects.order_by('-release_date').first()
        
        # Get all visible documentation sections with their related data
        sections = DocumentationSection.objects.filter(is_visible=True).prefetch_related(
            'subsections', 
            'subsections__items',
            'contacts'
        ).order_by('order')
        
        # Format the sections data for the template
        formatted_sections = []
        for section in sections:
            section_data = {
                'id': section.slug,
                'title': section.title,
                'content': section.content,
            }
            
            # Add subsections if they exist
            subsections = section.subsections.filter(is_visible=True).order_by('order')
            if subsections.exists():
                section_data['subsections'] = []
                for subsection in subsections:
                    subsection_data = {
                        'id': f"{section.slug}-{subsection.slug}",
                        'title': subsection.title,
                        'content': subsection.content,
                    }
                    
                    # Add items if they exist
                    items = subsection.items.all().order_by('order')
                    if items.exists():
                        subsection_data['items'] = [item.text for item in items]
                    
                    section_data['subsections'].append(subsection_data)
            
            # Add contacts if they exist
            contacts = section.contacts.all().order_by('order')
            if contacts.exists():
                section_data['contacts'] = []
                for contact in contacts:
                    contact_data = {'title': contact.title}
                    if contact.email:
                        contact_data['email'] = contact.email
                    if contact.phone:
                        contact_data['text'] = contact.phone
                    if contact.additional_info:
                        contact_data['additional_info'] = contact.additional_info
                    section_data['contacts'].append(contact_data)
            
            formatted_sections.append(section_data)
        
        context['title'] = "TTU Computer Lab Management System Documentation"
        context['sections'] = formatted_sections
        
        # Version information
        if current_version:
            context['version'] = {
                'number': current_version.version_number,
                'name': current_version.version_name,
                'date': current_version.release_date.strftime('%B %d, %Y'),
                'developer': current_version.developer,
                'type': current_version.get_version_type_display()
            }
        else:
            # Fallback version info if none exists
            context['version'] = {
                'number': '1.0.0',
                'date': 'May 27, 2025',
                'developer': 'TTU IT Department'
            }
        
        return context
