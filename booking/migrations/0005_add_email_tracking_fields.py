# Generated migration for email tracking fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0004_delete_systemevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='computerbooking',
            name='approval_email_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='computerbooking',
            name='rejection_email_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='computerbooking',
            name='cancellation_email_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='labsession',
            name='approval_email_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='labsession',
            name='rejection_email_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='labsession',
            name='cancellation_email_sent',
            field=models.BooleanField(default=False),
        ),
    ]
