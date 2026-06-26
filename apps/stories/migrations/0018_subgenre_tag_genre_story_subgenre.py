import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0017_story_cover_requests'),
    ]

    operations = [
        # 1. Create Subgenre table
        migrations.CreateModel(
            name='Subgenre',
            fields=[
                ('id',   models.BigAutoField(auto_created=True, primary_key=True,
                                             serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('genre', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subgenres',
                    to='stories.genre',
                )),
            ],
            options={'db_table': 'subgenres', 'ordering': ['name']},
        ),

        # 2. Add genre FK to Tag
        migrations.AddField(
            model_name='tag',
            name='genre',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tropes',
                to='stories.genre',
            ),
        ),

        # 3. Widen Tag.slug/name to accommodate longer trope names
        migrations.AlterField(
            model_name='tag',
            name='name',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='tag',
            name='slug',
            field=models.SlugField(max_length=120, unique=True),
        ),

        # 4. Add subgenre FK to Story
        migrations.AddField(
            model_name='story',
            name='subgenre',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='stories',
                to='stories.subgenre',
            ),
        ),
    ]
