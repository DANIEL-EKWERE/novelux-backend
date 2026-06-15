from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0013_story_lock_from_chapter'),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='chapters_per_week',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text='Author commitment: how many chapters they plan to publish per week (1–7).',
            ),
        ),
    ]
