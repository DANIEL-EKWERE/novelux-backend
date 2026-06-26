import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_authorprofile_completion_bonus'),
    ]

    operations = [
        # New personal fields
        migrations.AddField(
            model_name='authorkyc',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True, help_text='DOB as on your ID document'),
        ),
        # New ID image fields (front + back)
        migrations.AddField(
            model_name='authorkyc',
            name='id_front',
            field=models.ImageField(blank=True, upload_to='kyc/fronts/', help_text='Front of ID'),
        ),
        migrations.AddField(
            model_name='authorkyc',
            name='id_back',
            field=models.ImageField(blank=True, null=True, upload_to='kyc/backs/',
                                    help_text='Back of ID (not required for passport)'),
        ),
        # Make legacy id_document optional
        migrations.AlterField(
            model_name='authorkyc',
            name='id_document',
            field=models.ImageField(blank=True, upload_to='kyc/id_docs/',
                                    help_text='Legacy single-image field'),
        ),
        # OCR result fields
        migrations.AddField(
            model_name='authorkyc',
            name='ocr_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='authorkyc',
            name='ocr_dob',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='authorkyc',
            name='ocr_id_number',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='authorkyc',
            name='ocr_raw',
            field=models.JSONField(blank=True, default=dict),
        ),
        # Match score fields
        migrations.AddField(
            model_name='authorkyc',
            name='name_match_score',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='authorkyc',
            name='dob_match',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='authorkyc',
            name='overall_match_score',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='authorkyc',
            name='age_valid',
            field=models.BooleanField(blank=True, null=True),
        ),
        # Status choices update + new fields
        migrations.AlterField(
            model_name='authorkyc',
            name='status',
            field=models.CharField(
                max_length=15,
                choices=[
                    ('pending', 'Pending Submission'),
                    ('processing', 'Processing'),
                    ('under_review', 'Under SE Review'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                ],
                default='pending',
            ),
        ),
        migrations.AddField(
            model_name='authorkyc',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='authorkyc',
            name='reviewed_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='kyc_reviews',
                to=settings.AUTH_USER_MODEL,
                limit_choices_to={'role__in': ['se', 'ce', 'admin']},
            ),
        ),
    ]
