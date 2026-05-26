from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_user_editor_code_alter_user_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthorKYC',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(help_text='Real name as on your ID document', max_length=150)),
                ('phone', models.CharField(max_length=30)),
                ('contact_address', models.CharField(max_length=255)),
                ('country', models.CharField(max_length=100)),
                ('id_type', models.CharField(
                    choices=[('national_id', 'National ID Card'), ('passport', 'Passport'), ('drivers_license', "Driver's License")],
                    default='national_id',
                    max_length=20,
                )),
                ('id_number', models.CharField(max_length=60)),
                ('id_document', models.ImageField(
                    help_text='Photo of government-issued ID',
                    upload_to='kyc/id_docs/',
                )),
                ('payment_method', models.CharField(
                    choices=[('bank_account', 'Bank Account'), ('paypal', 'PayPal')],
                    default='bank_account',
                    max_length=20,
                )),
                ('account_holder', models.CharField(blank=True, max_length=150)),
                ('bank_name', models.CharField(blank=True, max_length=150)),
                ('account_number', models.CharField(blank=True, max_length=60)),
                ('swift_code', models.CharField(blank=True, max_length=11)),
                ('bank_country', models.CharField(blank=True, max_length=100)),
                ('paypal_email', models.EmailField(blank=True, max_length=254)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                    default='pending',
                    max_length=10,
                )),
                ('admin_notes', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='kyc',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'author_kyc',
            },
        ),
    ]
