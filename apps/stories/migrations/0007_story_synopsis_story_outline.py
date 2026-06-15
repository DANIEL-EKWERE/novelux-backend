from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0006_alter_platformsettings_review_threshold'),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='synopsis',
            field=models.TextField(blank=True, default='', help_text='Short hook shown on the story listing page.'),
        ),
        migrations.AddField(
            model_name='story',
            name='story_outline',
            field=models.TextField(blank=True, default='', help_text='Full narrative outline: how the story begins, develops, and ends. Used by SEs during review.'),
        ),
    ]
