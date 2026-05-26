from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('editorial', '0005_remove_authoreditorlink_assigned_ae_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='contractapplication',
            name='ce_signed_by',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'role': 'ce'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ce_signed_contracts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='contractapplication',
            name='ce_signed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
