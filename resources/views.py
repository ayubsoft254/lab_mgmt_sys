from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.

class DocumentationView(TemplateView):
    """
    View for displaying the system documentation.
    """
    template_name = "documentation.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "TTU Computer Lab Management System Documentation"
        context['sections'] = [
            {
                'id': 'introduction',
                'title': 'Introduction',
                'content': 'The TTU Computer Lab Management System is a comprehensive web application designed '
                          'specifically for Taita Taveta University to manage and optimize the use of computer '
                          'laboratory resources.'
            },
            {
                'id': 'system-overview',
                'title': 'System Overview',
                'content': 'Built on the Django web framework, this system provides a secure, scalable platform for '
                          'managing all aspects of computer lab operations at Taita Taveta University.'
            },
            {
                'id': 'features',
                'title': 'Features',
                'subsections': [
                    {
                        'id': 'core-features',
                        'title': 'Core Features',
                        'items': [
                            'Lab Computer Booking with real-time availability',
                            'User Management with email verification',
                            'Lab Administration tools',
                            'Analytics & Reporting dashboards',
                            'Communication tools including newsletter functionality'
                        ]
                    },
                    {
                        'id': 'additional-features',
                        'title': 'Additional Features',
                        'items': [
                            'Rating system for student feedback',
                            'FAQ section',
                            'Contact form for support',
                            'Mobile-responsive design'
                        ]
                    }
                ]
            },
            {
                'id': 'user-roles',
                'title': 'User Roles',
                'subsections': [
                    {
                        'id': 'students',
                        'title': 'Students',
                        'items': [
                            'Register and manage accounts',
                            'Book available computers',
                            'View booking history',
                            'Rate lab experiences',
                            'Subscribe to newsletters'
                        ]
                    },
                    {
                        'id': 'lab-administrators',
                        'title': 'Lab Administrators',
                        'items': [
                            'Approve/reject booking requests',
                            'Manage computer inventory',
                            'Schedule maintenance',
                            'View usage analytics',
                            'Communicate with students'
                        ]
                    },
                    {
                        'id': 'system-administrators',
                        'title': 'System Administrators',
                        'items': [
                            'Manage user accounts and permissions',
                            'Configure system settings',
                            'Access all administrative functions',
                            'Run system reports',
                            'Manage newsletter campaigns'
                        ]
                    }
                ]
            },
            {
                'id': 'technical-architecture',
                'title': 'Technical Architecture',
                'content': 'The system is built using Django, PostgreSQL, Tailwind CSS, and other modern technologies.'
            },
            {
                'id': 'user-guides',
                'title': 'User Guides',
                'subsections': [
                    {
                        'id': 'student-guide',
                        'title': 'Student Guide',
                        'content': 'Step-by-step instructions for students to register, book computers, and manage their bookings.'
                    },
                    {
                        'id': 'administrator-guide',
                        'title': 'Administrator Guide',
                        'content': 'Detailed guide for administrators on managing labs, bookings, and system settings.'
                    }
                ]
            },
            {
                'id': 'support',
                'title': 'Support & Maintenance',
                'content': 'Contact information for technical support and system administrators.',
                'contacts': [
                    {'title': 'Technical Support', 'email': 'itsupport@ttu.ac.ke'},
                    {'title': 'System Administrator', 'email': 'admin@ttu.ac.ke'},
                    {'title': 'Emergency Contact', 'text': 'Campus IT Help Desk (+254 XXXXXXXXX)'}
                ]
            }
        ]
        
        # Version information
        context['version'] = {
            'number': '1.0.0',
            'date': 'May 27, 2025',
            'developer': 'TTU IT Department'
        }
        
        return context
