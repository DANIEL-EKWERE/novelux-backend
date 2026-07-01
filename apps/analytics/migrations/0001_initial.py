from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PageVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('country', models.CharField(blank=True, db_index=True, max_length=100)),
                ('country_code', models.CharField(blank=True, max_length=2)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('path', models.CharField(db_index=True, max_length=500)),
                ('referrer', models.CharField(blank=True, max_length=500)),
                ('device_type', models.CharField(
                    blank=True, db_index=True, max_length=10,
                    choices=[('mobile', 'Mobile'), ('tablet', 'Tablet'), ('desktop', 'Desktop'), ('bot', 'Bot')],
                )),
                ('browser', models.CharField(blank=True, max_length=80)),
                ('os', models.CharField(blank=True, max_length=80)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='page_visits',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'page_visits', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='pagevisit',
            index=models.Index(fields=['created_at', 'country'], name='pv_created_country_idx'),
        ),
        migrations.AddIndex(
            model_name='pagevisit',
            index=models.Index(fields=['created_at', 'device_type'], name='pv_created_device_idx'),
        ),
    ]
