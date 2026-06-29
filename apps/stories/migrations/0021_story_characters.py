from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0020_story_book_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoryCharacter',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('story',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='story_characters', to='stories.story')),
                ('name',        models.CharField(max_length=100)),
                ('role',        models.CharField(blank=True, default='', max_length=20, choices=[
                    ('protagonist',   'Protagonist'),
                    ('antagonist',    'Antagonist'),
                    ('supporting',    'Supporting'),
                    ('love_interest', 'Love Interest'),
                    ('mentor',        'Mentor'),
                    ('villain',       'Villain'),
                    ('other',         'Other'),
                ])),
                ('age',         models.PositiveSmallIntegerField(blank=True, null=True)),
                ('gender',      models.CharField(blank=True, default='', max_length=30)),
                ('description', models.TextField(blank=True, default='')),
                ('image',       models.ImageField(blank=True, null=True, upload_to='characters/')),
                ('order',       models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'db_table': 'story_characters',
                'ordering': ['order', 'id'],
            },
        ),
    ]
