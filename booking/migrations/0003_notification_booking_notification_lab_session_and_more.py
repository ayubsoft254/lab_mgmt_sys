# Generated by Django 5.1.7 on 2025-05-22 18:09

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_recurringsession'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='booking',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notifications', to='booking.computerbooking'),
        ),
        migrations.AddField(
            model_name='notification',
            name='lab_session',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notifications', to='booking.labsession'),
        ),
        migrations.AddField(
            model_name='notification',
            name='recurring_session',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notifications', to='booking.recurringsession'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(choices=[('new_booking', 'New Booking'), ('booking_cancelled', 'Booking Cancelled'), ('session_booked', 'Session Booked'), ('booking_approved', 'Booking Approved'), ('booking_rejected', 'Booking Rejected'), ('recurring_session_created', 'Recurring Session Created'), ('recurring_session_approved', 'Recurring Session Approved'), ('recurring_session_rejected', 'Recurring Session Rejected')], max_length=50),
        ),
        migrations.CreateModel(
            name='SystemEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('login', 'User Login'), ('logout', 'User Logout'), ('registration', 'User Registration'), ('booking_created', 'Booking Created'), ('booking_approved', 'Booking Approved'), ('booking_rejected', 'Booking Rejected'), ('booking_cancelled', 'Booking Cancelled'), ('session_created', 'Lab Session Created'), ('session_approved', 'Lab Session Approved'), ('session_rejected', 'Lab Session Rejected'), ('maintenance_request', 'Maintenance Request'), ('maintenance_resolved', 'Maintenance Resolved'), ('system_error', 'System Error')], max_length=50)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('details', models.JSONField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='system_events', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
