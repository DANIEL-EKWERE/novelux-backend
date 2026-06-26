import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('editorial', '0010_sepromreq_tab_section_exploretabpin'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('stories', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromotionSlotConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('featured', 'Featured For You'), ('best-novel', 'Best Novel'), ('trending', 'Trending Now'), ('short-stories', 'Short Stories'), ('ranking', 'Ranking'), ('editors-pick', "Editor's Pick"), ('werewolf', 'Werewolf'), ('billionaire', 'Billionaire'), ('short-fics', 'Short Fics'), ('for-her', 'For Her'), ('for-him', 'For Him'), ('suspense', 'Suspense')], max_length=30)),
                ('slot_limit', models.PositiveSmallIntegerField(default=5)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('se', models.ForeignKey(blank=True, limit_choices_to={'role': 'se'}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='promo_slot_configs', to=settings.AUTH_USER_MODEL)),
                ('set_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='promo_slot_configs_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'promotion_slot_configs'},
        ),
        migrations.AddConstraint(
            model_name='promotionslotconfig',
            constraint=models.UniqueConstraint(fields=['category', 'se'], name='unique_category_se_slot'),
        ),
        migrations.CreateModel(
            name='StoryPromotion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('featured', 'Featured For You'), ('best-novel', 'Best Novel'), ('trending', 'Trending Now'), ('short-stories', 'Short Stories'), ('ranking', 'Ranking'), ('editors-pick', "Editor's Pick"), ('werewolf', 'Werewolf'), ('billionaire', 'Billionaire'), ('short-fics', 'Short Fics'), ('for-her', 'For Her'), ('for-him', 'For Him'), ('suspense', 'Suspense')], max_length=30)),
                ('status', models.CharField(choices=[('active', 'Active'), ('queued', 'Queued'), ('expired', 'Expired')], default='active', max_length=10)),
                ('starts_at', models.DateTimeField()),
                ('expires_at', models.DateTimeField()),
                ('queue_position', models.PositiveSmallIntegerField(default=0)),
                ('reminder_sent', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('se', models.ForeignKey(limit_choices_to={'role': 'se'}, on_delete=django.db.models.deletion.CASCADE, related_name='story_promotions', to=settings.AUTH_USER_MODEL)),
                ('story', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promotions', to='stories.story')),
            ],
            options={'db_table': 'story_promotions', 'ordering': ['queue_position', 'created_at']},
        ),
    ]
