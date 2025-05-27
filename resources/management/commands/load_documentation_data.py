import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from resources.models import SystemVersion, DocumentationSection, SubSection, DocumentationItem, ContactInfo

class Command(BaseCommand):
    help = 'Loads initial documentation data into the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting documentation data population...'))
        self.populate_documentation()
        self.stdout.write(self.style.SUCCESS('Documentation populated successfully!'))

    def populate_documentation(self):  
        # Delete existing data to avoid duplications
        self.stdout.write('Removing existing documentation data...')
        DocumentationSection.objects.all().delete()
        
        # Create initial system version
        version, created = SystemVersion.objects.get_or_create(
            version_number='1.0.0',
            defaults={
                'version_name': 'Initial Release',
                'version_type': 'major',
                'release_date': timezone.now().date(),
                'is_current': True,
                'developer': 'Ayub Henry',
                'release_notes': 'Initial release of the TTU Computer Lab Management System'
            }
        )
        if created:
            self.stdout.write(f'Created system version: {version}')
        
        # Create sections and subsections
        sections_data = [
            {
                "title": "Introduction",
                "order": 1,
                "content": "The TTU Computer Lab Management System is a comprehensive, secure, and user-friendly web application developed for Taita Taveta University. It streamlines the management of computer laboratory resources including computer bookings, lab sessions, analytics, and communication between users and administrators.\n\nThis document serves as a complete reference for end-users, lab administrators, and system maintainers.",
                "subsections": []
            },
            {
                "title": "System Overview",
                "order": 2,
                "content": "Built on Django 5.1, the system provides a modular, scalable platform tailored for university lab environments.",
                "subsections": [
                    {
                        "title": "Features",
                        "order": 1,
                        "content": "",
                        "items": [
                            "Real-time lab and system availability",
                            "Booking confirmations & cancellations",
                            "Historical booking tracking",
                            "Automated email reminders"
                        ]
                    }
                ]
            },
            {
                "title": "Features",
                "order": 3,
                "content": "",
                "subsections": [
                    {
                        "title": "Core Features",
                        "order": 1,
                        "content": "",
                        "items": [
                            "Lab Computer Booking",
                            "User Management",
                            "Lab Administration",
                            "Analytics & Reporting",
                            "Communication"
                        ]
                    },
                    {
                        "title": "Additional Features",
                        "order": 2,
                        "content": "",
                        "items": [
                            "Student feedback & ratings",
                            "Mobile responsive UI",
                            "FAQ & support contact form"
                        ]
                    }
                ]
            },
            {
                "title": "User Roles",
                "order": 4,
                "content": "",
                "subsections": [
                    {
                        "title": "Students",
                        "order": 1,
                        "content": "",
                        "items": [
                            "Register and manage accounts",
                            "Book and view computer sessions",
                            "Rate lab experiences",
                            "Subscribe to newsletters"
                        ]
                    },
                    {
                        "title": "Lab Administrators",
                        "order": 2,
                        "content": "",
                        "items": [
                            "Approve or reject bookings",
                            "Manage computer inventory",
                            "Schedule maintenance and lab hours",
                            "Access lab usage analytics",
                            "Communicate with students"
                        ]
                    },
                    {
                        "title": "System Administrators",
                        "order": 3,
                        "content": "",
                        "items": [
                            "Manage all user accounts and permissions",
                            "Configure core system settings",
                            "Access all backend reports and logs",
                            "Oversee newsletter campaigns"
                        ]
                    }
                ]
            },
            {
                "title": "Technical Architecture",
                "order": 5,
                "content": "",
                "subsections": [
                    {
                        "title": "Technology Stack",
                        "order": 1,
                        "content": "",
                        "items": [
                            "Backend: Django 5.1",
                            "Database: PostgreSQL (Production) / SQLite (Development)",
                            "Frontend: HTML, Tailwind CSS, JavaScript",
                            "Queue Management: Celery with Redis",
                            "Email System: SMTP with Django Allauth",
                            "Deployment: HTTPS-enabled WSGI server"
                        ]
                    },
                    {
                        "title": "System Components",
                        "order": 2,
                        "content": "",
                        "items": [
                            "booking: Manages lab reservations",
                            "analytics: Gathers and visualizes usage metrics",
                            "contact: Handles user inquiries",
                            "newsletter: Subscription and campaign management"
                        ]
                    },
                    {
                        "title": "Security Features",
                        "order": 3,
                        "content": "",
                        "items": [
                            "SSL/TLS Encryption",
                            "CSRF Protection",
                            "Role-Based Access",
                            "Email Verification"
                        ]
                    },
                    {
                        "title": "Background Tasks",
                        "order": 4,
                        "content": "",
                        "items": [
                            "Booking reminders",
                            "Session end alerts",
                            "Automated report generation",
                            "Newsletter distribution"
                        ]
                    }
                ]
            },
            {
                "title": "Installation & Setup",
                "order": 6,
                "content": "",
                "subsections": [
                    {
                        "title": "Prerequisites",
                        "order": 1,
                        "content": "",
                        "items": [
                            "Python 3.10+",
                            "PostgreSQL",
                            "Redis",
                            "SMTP server"
                        ]
                    },
                    {
                        "title": "Environment Variables",
                        "order": 2,
                        "content": "Use a .env file to manage sensitive settings:",
                        "items": [
                            "DJANGO_SECRET_KEY",
                            "DATABASE_URL",
                            "EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD",
                            "ADMIN_USER_NAME, ADMIN_USER_EMAIL",
                            "BASE_URL"
                        ]
                    },
                    {
                        "title": "Deployment Steps",
                        "order": 3,
                        "content": "",
                        "items": [
                            "Clone repository",
                            "Set up .env variables",
                            "Install dependencies: pip install -r requirements.txt",
                            "Apply migrations: python manage.py migrate",
                            "Collect static files: python manage.py collectstatic",
                            "Start background workers: celery -A src worker -l info",
                            "celery -A src beat -l info",
                            "Deploy using Gunicorn or another WSGI server"
                        ]
                    }
                ]
            },
            {
                "title": "User Guides",
                "order": 7,
                "content": "",
                "subsections": [
                    {
                        "title": "Student Guide",
                        "order": 1,
                        "content": "",
                        "subsubsections": [
                            {
                                "title": "Registration",
                                "order": 1,
                                "content": "",
                                "items": [
                                    "Visit the registration page",
                                    "Verify email via confirmation link",
                                    "Complete your profile"
                                ]
                            },
                            {
                                "title": "Booking a Computer",
                                "order": 2,
                                "content": "",
                                "items": [
                                    "Log in and view available labs",
                                    "Select your preferred time and system",
                                    "Confirm booking",
                                    "Receive confirmation email"
                                ]
                            },
                            {
                                "title": "Managing Bookings",
                                "order": 3,
                                "content": "",
                                "items": [
                                    "Access dashboard to view bookings",
                                    "Cancel or update future bookings",
                                    "Provide feedback after session"
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Administrator Guide",
                        "order": 2,
                        "content": "",
                        "subsubsections": [
                            {
                                "title": "Lab & Computer Management",
                                "order": 1,
                                "content": "",
                                "items": [
                                    "Add/edit lab details",
                                    "Manage computer inventory",
                                    "Define operating hours"
                                ]
                            },
                            {
                                "title": "Booking Oversight",
                                "order": 2,
                                "content": "",
                                "items": [
                                    "View and manage all reservations",
                                    "Approve/reject requests",
                                    "Resolve booking conflicts",
                                    "Export booking reports"
                                ]
                            },
                            {
                                "title": "Newsletter Campaigns",
                                "order": 3,
                                "content": "",
                                "items": [
                                    "Create & segment subscriber lists",
                                    "Schedule and send campaigns",
                                    "Monitor open and click rates"
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Troubleshooting",
                "order": 8,
                "content": "",
                "subsections": [
                    {
                        "title": "Booking Conflicts",
                        "order": 1,
                        "content": "",
                        "items": [
                            "Check for overlapping times",
                            "Ensure lab availability is up-to-date"
                        ]
                    },
                    {
                        "title": "Email Issues",
                        "order": 2,
                        "content": "",
                        "items": [
                            "Validate SMTP settings",
                            "Inspect spam folders",
                            "Confirm valid email entries"
                        ]
                    },
                    {
                        "title": "Performance",
                        "order": 3,
                        "content": "",
                        "items": [
                            "Monitor resource usage (RAM/CPU)",
                            "Optimize heavy queries",
                            "Use static file caching"
                        ]
                    },
                    {
                        "title": "Logs",
                        "order": 4,
                        "content": "",
                        "items": [
                            "Logs stored in /var/logs/ictlabs/",
                            "Error alerts sent to admin email",
                            "Debug mode for local environments"
                        ]
                    }
                ]
            },
            {
                "title": "Support & Maintenance",
                "order": 9,
                "content": "",
                "subsections": [
                    {
                        "title": "Contact",
                        "order": 1,
                        "content": "",
                        "items": [
                            "Technical Support: ictlabs@ttu.ac.ke",
                            "System Admin: ictlabs@ttu.ac.ke"
                        ]
                    },
                    {
                        "title": "Maintenance",
                        "order": 2,
                        "content": "",
                        "items": [
                            "Routine Updates: 1st Sunday of every month",
                            "Emergency Patches: As needed",
                            "Downtime Alerts: Announced via newsletter and site banner"
                        ]
                    }
                ],
                "contacts": [
                    {
                        "title": "Technical Support",
                        "email": "ictlabs@ttu.ac.ke",
                        "additional_info": "",
                        "order": 1
                    },
                    {
                        "title": "System Administrator",
                        "email": "ictlabs@ttu.ac.ke",
                        "additional_info": "",
                        "order": 2
                    }
                ]
            }
        ]

        for section_data in sections_data:
            section = DocumentationSection.objects.create(
                title=section_data['title'],
                order=section_data['order'],
                content=section_data.get('content', '')
            )
            self.stdout.write(f'Created section: {section.title}')
            
            for subsection_data in section_data.get('subsections', []):
                subsection = SubSection.objects.create(
                    section=section,
                    title=subsection_data['title'],
                    order=subsection_data['order'],
                    content=subsection_data.get('content', '')
                )
                self.stdout.write(f'  - Created subsection: {subsection.title}')
                
                # Handle items for this subsection
                for item_text in subsection_data.get('items', []):
                    DocumentationItem.objects.create(
                        subsection=subsection,
                        text=item_text,
                        order=DocumentationItem.objects.filter(subsection=subsection).count() + 1
                    )
                
                # Handle nested sub-subsections (like in User Guides)
                for subsubsection_data in subsection_data.get('subsubsections', []):
                    subsubsection = SubSection.objects.create(
                        section=section,
                        title=subsubsection_data['title'],
                        order=subsubsection_data['order'],
                        content=subsubsection_data.get('content', '')
                    )
                    self.stdout.write(f'    - Created nested subsection: {subsubsection.title}')
                    
                    for item_text in subsubsection_data.get('items', []):
                        DocumentationItem.objects.create(
                            subsection=subsubsection,
                            text=item_text,
                            order=DocumentationItem.objects.filter(subsection=subsubsection).count() + 1
                        )
            
            # Handle contact information if it exists
            for contact_data in section_data.get('contacts', []):
                ContactInfo.objects.create(
                    section=section,
                    title=contact_data['title'],
                    email=contact_data.get('email', ''),
                    additional_info=contact_data.get('additional_info', ''),
                    order=contact_data['order']
                )