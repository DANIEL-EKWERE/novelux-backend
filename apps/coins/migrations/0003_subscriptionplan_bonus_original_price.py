from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coins', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionplan',
            name='bonus_coins',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='original_price_usd',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]
