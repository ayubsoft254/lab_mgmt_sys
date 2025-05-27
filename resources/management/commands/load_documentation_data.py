import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from resources.models import SystemVersion, DocumentationSection, SubSection, DocumentationItem, ContactInfo

class Command(BaseCommand):
    help = 'Loads initial documentation data into the database'

    def handle(self, *args, **options):
        # Create initial version
        version, created = SystemVersion.objects.get_or_create(
            version_number='1.0.0',
            defaults={
                'version_name': 'Initial Release',
                'version_type': 'major',
                'release_date': timezone.now().date(),
                'is_current': True,
                'developer': 'TTU IT Department',
                'release_notes': 'Initial release of the TTU Computer Lab Management System'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created system version: {version}'))
        
        # Create introduction section
        intro_section, created = DocumentationSection.objects.get_or_create(
            title='Introduction',
            defaults={
                'order': 1,
                'content': 'The TTU Computer Lab Management System is a comprehensive web application designed '
                          'specifically for Taita Taveta University to manage and optimize the use of computer '
                          'laboratory resources.'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created section: {intro_section}'))
        
        # Create system overview section
        overview, created = DocumentationSection.objects.get_or_create(
            title='System Overview',
            defaults={
                'order': 2,
                'content': 'Built on the Django web framework, this system provides a secure, scalable platform for '
                          'managing all aspects of computer lab operations at Taita Taveta University.'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created section: {overview}'))
        
        # Create features section with subsections
        features, created = DocumentationSection.objects.get_or_create(
            title='Features',
            defaults={'order': 3}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created section: {features}'))
            
            # Create core features subsection
            core_features = SubSection.objects.create(
                section=features,
                title='Core Features',
                order=1
            )
            
            # Add items to core features
            items = [
                'Lab Computer Booking with real-time availability',
                'User Management with email verification',
                'Lab Administration tools',
                'Analytics & Reporting dashboards',
                'Communication tools including newsletter functionality'
            ]
            for i, item_text in enumerate(items):
                DocumentationItem.objects.create(
                    subsection=core_features,
                    text=item_text,
                    order=i+1
                )
                
            # Create additional features subsection
            add_features = SubSection.objects.create(
                section=features,
                title='Additional Features',
                order=2
            )
            
            # Add items to additional features
            items = [
                'Rating system for student feedback',
                'FAQ section',
                'Contact form for support',
                'Mobile-responsive design'
            ]
            for i, item_text in enumerate(items):
                DocumentationItem.objects.create(
                    subsection=add_features,
                    text=item_text,
                    order=i+1
                )
        
        # Create support section with contacts
        support, created = DocumentationSection.objects.get_or_create(
            title='Support & Maintenance',
            defaults={
                'order': 7,
                'content': 'Contact information for technical support and system administrators.'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created section: {support}'))
            
            # Add contact information
            contacts = [
                {
                    'title': 'Technical Support',
                    'email': 'itsupport@ttu.ac.ke',
                    'order': 1
                },
                {
                    'title': 'System Administrator',
                    'email': 'admin@ttu.ac.ke',
                    'order': 2
                },
                {
                    'title': 'Emergency Contact',
                    'phone': 'Campus IT Help Desk (+254 XXXXXXXXX)',
                    'order': 3
                }
            ]
            for i, contact_data in enumerate(contacts):
                ContactInfo.objects.create(
                    section=support,
                    **contact_data
                )
                
        self.stdout.write(self.style.SUCCESS('Documentation data loaded successfully'))