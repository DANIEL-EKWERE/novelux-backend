from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_user_device_tracking'),
    ]

    operations = [
        migrations.AddField(
            model_name='authorprofile',
            name='completion_bonus',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
