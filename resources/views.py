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
                    "Affected students may appeal their suspension through the university IC department, but reinstatement is not guaranteed"
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

class PrivacyPolicyView(TemplateView):
    """
    View for displaying the system Privacy Policy.
    """
    template_name = "privacy_policy.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the current system version
        current_version = SystemVersion.objects.filter(is_current=True).first()
        if not current_version:
            # Fallback if no version is marked as current
            current_version = SystemVersion.objects.order_by('-release_date').first()
        
        context['title'] = "Privacy Policy - TTU Computer Lab Management System"
        
        # Privacy policy sections
        context['privacy_sections'] = [
            {
                "id": "information-collected",
                "title": "1. Information We Collect",
                "content": "The TTU Computer Lab Management System collects the following information:",
                "items": [
                    "Personal identification information (name, email address, student ID)",
                    "Authentication credentials (password hash, not the actual password)",
                    "Academic information (department, course, year of study)",
                    "System usage data (lab bookings, login times, usage patterns)",
                    "Device information (IP address, browser type, operating system)"
                ]
            },
            {
                "id": "information-use",
                "title": "2. How We Use Your Information",
                "content": "The information collected is used for:",
                "items": [
                    "Managing and processing lab bookings",
                    "Authenticating users and securing accounts",
                    "Sending notifications and reminders about bookings",
                    "Generating usage analytics to optimize lab resources",
                    "Investigating policy violations when necessary",
                    "Improving system functionality and user experience"
                ]
            },
            {
                "id": "data-security",
                "title": "3. Data Security",
                "content": "We implement security measures including:",
                "items": [
                    "Password encryption using industry-standard hashing algorithms",
                    "Secure HTTPS connections for all system interactions",
                    "Regular security audits and vulnerability testing",
                    "Access controls limiting staff access to personal data",
                    "Data backup procedures to prevent accidental loss"
                ]
            },
            {
                "id": "data-sharing",
                "title": "4. Data Sharing and Disclosure",
                "content": "Your information may be shared with:",
                "items": [
                    "University IT staff responsible for system maintenance",
                    "Lab administrators for booking management purposes",
                    "Academic staff when relevant to academic requirements",
                    "Third parties when required by law or university regulations",
                    "Third-party service providers that help operate our system (with strict data protection agreements)"
                ]
            },
            {
                "id": "user-rights",
                "title": "5. Your Rights",
                "content": "As a user, you have the right to:",
                "items": [
                    "Access personal data stored about you in the system",
                    "Request correction of inaccurate information",
                    "Request deletion of your account (subject to academic record requirements)",
                    "Export your booking history and system usage data",
                    "Opt out of non-essential communications"
                ]
            },
            {
                "id": "data-retention",
                "title": "6. Data Retention",
                "content": "We retain your information according to the following principles:",
                "items": [
                    "Active student accounts are maintained for the duration of enrollment",
                    "Booking records are kept for 2 academic years for reference and analytics",
                    "Account data is archived when students graduate or leave the university",
                    "Inactive accounts may be permanently deleted after 3 years of no activity",
                    "Anonymous usage statistics may be kept indefinitely for historical analysis"
                ]
            },
            {
                "id": "cookies-tracking",
                "title": "7. Cookies and Tracking",
                "content": "Our system uses the following cookies and tracking technologies:",
                "items": [
                    "Essential session cookies to maintain your logged-in state",
                    "Authentication cookies to verify your identity",
                    "Preference cookies to remember your settings",
                    "Analytics cookies to improve system performance (anonymized)",
                    "You can disable non-essential cookies through your browser settings"
                ]
            },
            {
                "id": "policy-changes",
                "title": "8. Changes to This Policy",
                "content": "We may update our Privacy Policy periodically:",
                "items": [
                    "Significant changes will be announced through the system dashboard",
                    "Email notifications will be sent for material policy updates",
                    "The last updated date will reflect when changes were made",
                    "Previous versions of the policy are available upon request",
                    "Continued use of the system after policy changes constitutes acceptance"
                ]
            },
            {
                "id": "contact-information",
                "title": "9. Contact Information",
                "content": "For privacy-related inquiries, please contact:",
                "contact_info": {
                    "name": "Data Protection Officer",
                    "email": "ictlabs@ttu.ac.ke",
                    "department": "IC Department, Taita Taveta University",
                    "address": "P.O. Box 635-80300, Voi, Kenya"
                }
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