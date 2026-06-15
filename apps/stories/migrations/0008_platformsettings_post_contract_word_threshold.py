from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0007_story_synopsis_story_outline'),
    ]

    operations = [
        migrations.AddField(
            model_name='platformsettings',
            name='post_contract_word_threshold',
            field=models.PositiveIntegerField(
                default=10000,
                help_text='Total word count a signed story must reach before it goes live (status → ongoing) and held chapters are published.',
            ),
        ),
    ]
