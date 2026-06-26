from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coins', '0003_subscriptionplan_bonus_original_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchase',
            name='iap_transaction_id',
            field=models.CharField(blank=True, db_index=True, max_length=200),
        ),
    ]
