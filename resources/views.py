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

class TermsConditionsView(TemplateView):
    """
    View for displaying the system Terms and Conditions.
    """
    template_name = "terms_conditions.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the current system version
        current_version = SystemVersion.objects.filter(is_current=True).first()
        if not current_version:
            # Fallback if no version is marked as current
            current_version = SystemVersion.objects.order_by('-release_date').first()
        
        context['title'] = "Terms & Conditions - TTU Computer Lab Management System"
        
        # Terms and conditions sections
        context['terms_sections'] = [
            {
                "id": "system-use",
                "title": "1. System Use",
                "content": "By using this system, you agree to:",
                "items": [
                    "Book lab sessions responsibly and only when you intend to attend",
                    "Use your own credentials and never share login details with others",
                    "Abide by all university lab conduct and ICT policies"
                ]
            },
            {
                "id": "admin-rights",
                "title": "2. Admin Rights",
                "content": "Lab Administrators may:",
                "items": [
                    "Cancel or modify bookings in case of conflict or misuse",
                    "Monitor usage logs for reporting and system optimization",
                    "Temporarily or permanently suspend accounts found to be violating usage terms"
                ]
            },
            {
                "id": "booking-discipline",
                "title": "3. Booking Discipline Policy",
                "content": "To ensure fair access to limited lab resources:",
                "items": [
                    "If a student books a computer three (3) consecutive times without checking in, their account will be automatically suspended for the remainder of the semester",
                    "Affected students may appeal their suspension through the university ICT department, but reinstatement is not guaranteed"
                ]
            },
            {
                "id": "acceptable-use",
                "title": "4. Acceptable Use",
                "content": "You must not:",
                "items": [
                    "Attempt to hack, tamper with, or reverse engineer any part of the system",
                    "Upload or distribute malicious or inappropriate content",
                    "Use the platform for commercial, political, or unauthorized academic purposes"
                ]
            },
            {
                "id": "service-interruptions",
                "title": "5. Service Interruptions",
                "content": "System access may be limited during:",
                "items": [
                    "Routine maintenance (users will be notified in advance)",
                    "Emergency repairs (communicated via system banners or email)",
                    "Network or infrastructure issues beyond university control"
                ]
            },
            {
                "id": "limitation-liability",
                "title": "6. Limitation of Liability",
                "content": "The university is not liable for:",
                "items": [
                    "Missed bookings caused by student negligence or device issues",
                    "Data loss due to unforeseen system breaches or hardware failure",
                    "Penalties or academic consequences from missed lab sessions"
                ]
            }
        ]
        
        # Version information
        if current_version:
            context['version'] = {
                'number': current_version.version_number,
                'date': current_version.release_date.strftime('%B %d, %Y')
            }
        else:
            # Fallback version info if none exists
            context['version'] = {
                'number': '1.0.0',
                'date': 'May 27, 2025'
            }
        
        return context
