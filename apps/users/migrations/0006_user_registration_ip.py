import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_authorkkyc'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='registration_ip',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_banned',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='ban_reason',
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name='BlacklistedIP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(unique=True)),
                ('reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('blacklisted_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ip_blacklists',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'blacklisted_ips'},
        ),
    ]
