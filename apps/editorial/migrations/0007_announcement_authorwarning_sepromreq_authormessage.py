from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('editorial', '0006_contractapplication_ce_sign'),
        ('stories', '0014_story_chapters_per_week'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('target', models.CharField(choices=[('all', 'Everyone'), ('authors', 'Authors only'), ('ses', 'Senior Editors only')], default='all', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_sent', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('sent_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='announcements', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'announcements', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AuthorWarning',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[('plagiarism', 'Plagiarism'), ('ai_content', 'AI-Generated Content'), ('misconduct', 'Misconduct'), ('inactivity', 'Inactivity'), ('other', 'Other')], max_length=20)),
                ('details', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='warnings', to=settings.AUTH_USER_MODEL)),
                ('issued_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='issued_warnings', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'author_warnings', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='SEPromotionRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('ce_note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('se', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promotion_requests', to=settings.AUTH_USER_MODEL)),
                ('story', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promotion_requests', to='stories.story')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_promotions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'se_promotion_requests', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AuthorMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('msg_type', models.CharField(choices=[('complaint', 'Complaint'), ('question', 'Question'), ('report', 'Report'), ('other', 'Other')], default='other', max_length=10)),
                ('is_read', models.BooleanField(default=False)),
                ('ce_reply', models.TextField(blank=True)),
                ('replied_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='author_messages', to=settings.AUTH_USER_MODEL)),
                ('replied_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='message_replies', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'author_messages', 'ordering': ['-created_at']},
        ),
    ]
