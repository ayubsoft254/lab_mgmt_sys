# Generated migration file for new Inquiry and Feedback models

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Inquiry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('category', models.CharField(choices=[('general', 'General Inquiry'), ('technical', 'Technical Support'), ('booking', 'Booking Assistance'), ('account', 'Account/Profile'), ('other', 'Other')], default='general', max_length=20)),
                ('subject', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('in_progress', 'In Progress'), ('resolved', 'Resolved'), ('closed', 'Closed')], default='open', max_length=20)),
                ('admin_response', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('admin_responder', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inquiry_responses', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inquiries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Inquiries',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=100)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('category', models.CharField(choices=[('bug', 'Bug Report'), ('feature', 'Feature Request'), ('ui', 'UI/UX Improvement'), ('performance', 'Performance Issue'), ('other', 'Other')], default='other', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('rating', models.IntegerField(choices=[(1, '1 - Poor'), (2, '2 - Fair'), (3, '3 - Good'), (4, '4 - Very Good'), (5, '5 - Excellent')], default=3)),
                ('admin_notes', models.TextField(blank=True, null=True)),
                ('is_actionable', models.BooleanField(default=False, help_text='Mark if this feedback requires action')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='feedbacks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
