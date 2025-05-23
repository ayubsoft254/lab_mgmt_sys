from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from booking.models import User

class Command(BaseCommand):
    help = 'Creates a super admin user with all permissions'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the super admin')
        parser.add_argument('email', type=str, help='Email for the super admin')
        parser.add_argument('password', type=str, help='Password for the super admin')

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        email = kwargs['email']
        password = kwargs['password']
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User with username {username} already exists'))
            return
        
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        
        user.is_admin = True
        user.is_super_admin = True
        user.save()
        
        self.stdout.write(self.style.SUCCESS(f'Super admin {username} created successfully'))