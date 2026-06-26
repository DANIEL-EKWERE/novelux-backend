import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import ckeditor.fields


class Migration(migrations.Migration):

    dependencies = [
        ('chapters', '0006_alter_chapter_is_locked'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChapterEditRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('pending_title',   models.CharField(blank=True, max_length=255)),
                ('pending_content', ckeditor.fields.RichTextField()),
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
                    related_name='chapter_edit_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('chapter', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='edit_requests',
                    to='chapters.chapter',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='chapter_edit_reviews',
                    to=settings.AUTH_USER_MODEL,
                    limit_choices_to={'role__in': ['se', 'ce']},
                )),
            ],
            options={'db_table': 'chapter_edit_requests', 'ordering': ['-submitted_at']},
        ),
    ]
