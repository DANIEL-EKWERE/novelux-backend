from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0012_alter_story_contract_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='lock_from_chapter',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text='Chapter number at which locking starts. NULL = all free. 1 = all locked. 5 = chapters 1-4 free, 5+ locked.',
            ),
        ),
    ]
