import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0016_promotion_expiry_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StoryCoverRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('pending_cover', models.ImageField(upload_to='covers/pending/')),
                ('status', models.CharField(
                    choices=[
                        ('pending',  'Pending SE Review'),
                        ('approved', 'Approved'),
                        ('rejected', 'Rejected'),
                    ],
                    db_index=True, default='pending', max_length=10,
                )),
                ('se_note',      models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at',  models.DateTimeField(blank=True, null=True)),
                ('author', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cover_change_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('story', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cover_requests',
                    to='stories.story',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='cover_request_reviews',
                    to=settings.AUTH_USER_MODEL,
                    limit_choices_to={'role__in': ['se', 'ce']},
                )),
            ],
            options={'db_table': 'story_cover_requests', 'ordering': ['-submitted_at']},
        ),
    ]
