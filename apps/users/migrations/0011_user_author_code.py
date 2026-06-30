import secrets
import string

from django.db import migrations, models

_CHARS = string.ascii_uppercase + string.digits


def _gen():
    return 'A-' + ''.join(secrets.choice(_CHARS) for _ in range(7))


def backfill_author_codes(apps, schema_editor):
    User = apps.get_model('users', 'User')
    used = set()
    for user in User.objects.filter(role='author', author_code__isnull=True).order_by('id'):
        while True:
            code = _gen()
            if code not in used and not User.objects.filter(author_code=code).exists():
                used.add(code)
                break
        user.author_code = code
        user.save(update_fields=['author_code'])


def add_like_index(apps, schema_editor):
    db = schema_editor.connection.vendor
    if db == 'postgresql':
        schema_editor.execute(
            "CREATE INDEX IF NOT EXISTS users_author_code_like "
            "ON users USING btree (author_code varchar_pattern_ops);"
        )


def drop_like_index(apps, schema_editor):
    db = schema_editor.connection.vendor
    if db == 'postgresql':
        schema_editor.execute(
            "DROP INDEX IF EXISTS users_author_code_like;"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_authorkkyc_kyc_v2'),
    ]

    operations = [
        # 1. Add column
        migrations.AddField(
            model_name='user',
            name='author_code',
            field=models.CharField(
                blank=True, null=True, max_length=12,
                help_text='Unique public ID for author accounts (e.g. A-NLX4K8P).',
            ),
        ),

        # 2. Backfill existing author accounts
        migrations.RunPython(backfill_author_codes, migrations.RunPython.noop),

        # 3. Add unique constraint + db_index
        migrations.AlterField(
            model_name='user',
            name='author_code',
            field=models.CharField(
                blank=True, null=True, db_index=True, max_length=12, unique=True,
                help_text='Unique public ID for author accounts (e.g. A-NLX4K8P).',
            ),
        ),

        # 4. PostgreSQL-only: varchar_pattern_ops index for prefix LIKE searches
        migrations.RunPython(add_like_index, drop_like_index),
    ]
