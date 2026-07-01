from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coins', '0004_purchase_iap_transaction_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CheckinStreak',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_streak', models.PositiveIntegerField(default=0)),
                ('longest_streak', models.PositiveIntegerField(default=0)),
                ('last_checkin', models.DateField(null=True, blank=True)),
                ('total_checkins', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='checkin_streak',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'checkin_streaks'},
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('task_type', models.CharField(
                    max_length=10,
                    choices=[('action', 'Action'), ('response', 'Response')],
                    default='action',
                )),
                ('reward_coins', models.PositiveIntegerField(default=10)),
                ('icon', models.CharField(blank=True, max_length=10)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('is_repeatable', models.BooleanField(default=False)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='tasks_created',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'tasks', 'ordering': ['order', '-created_at']},
        ),
        migrations.CreateModel(
            name='UserTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    max_length=10,
                    choices=[('pending', 'Pending'), ('completed', 'Completed'), ('claimed', 'Claimed')],
                    default='pending',
                )),
                ('response', models.TextField(blank=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('claimed_at', models.DateTimeField(blank=True, null=True)),
                ('task', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='completions',
                    to='coins.task',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='user_tasks',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'user_tasks', 'unique_together': {('user', 'task')}},
        ),
    ]
