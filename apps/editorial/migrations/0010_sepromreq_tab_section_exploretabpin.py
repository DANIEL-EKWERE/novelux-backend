from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('editorial', '0009_system_notice'),
        ('stories', '0016_promotion_expiry_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add tab + section to SEPromotionRequest
        migrations.AddField(
            model_name='sepromotionrequest',
            name='tab',
            field=models.CharField(
                choices=[
                    ('werewolf', 'Werewolf'), ('billionaire', 'Billionaire'),
                    ('short-fics', 'Short Fics'), ('ranking', 'Ranking'),
                    ('for-her', 'For Her'), ('for-him', 'For Him'),
                    ('suspense', 'Suspense'),
                ],
                default='werewolf',
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sepromotionrequest',
            name='section',
            field=models.CharField(
                default='',
                help_text='Section slug, e.g. picks-for-you, fresh-reads',
                max_length=50,
            ),
            preserve_default=False,
        ),
        # Create ExploreTabPin
        migrations.CreateModel(
            name='ExploreTabPin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tab', models.CharField(
                    choices=[
                        ('werewolf', 'Werewolf'), ('billionaire', 'Billionaire'),
                        ('short-fics', 'Short Fics'), ('ranking', 'Ranking'),
                        ('for-her', 'For Her'), ('for-him', 'For Him'),
                        ('suspense', 'Suspense'),
                    ],
                    db_index=True,
                    max_length=20,
                )),
                ('section', models.CharField(db_index=True, max_length=50)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('order', models.PositiveSmallIntegerField(default=0, help_text='Lower = higher in section')),
                ('pinned_at', models.DateTimeField(auto_now_add=True)),
                ('pinned_by', models.ForeignKey(
                    limit_choices_to={'role': 'ce'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tab_pins_added',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('source_request', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='resulting_pin',
                    to='editorial.sepromotionrequest',
                )),
                ('story', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tab_pins',
                    to='stories.story',
                )),
            ],
            options={
                'db_table': 'explore_tab_pins',
                'ordering': ['order', '-pinned_at'],
                'unique_together': {('tab', 'section', 'story')},
            },
        ),
    ]
