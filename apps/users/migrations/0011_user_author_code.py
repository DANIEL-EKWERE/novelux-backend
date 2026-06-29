import secrets
import string

from django.db import migrations, models

_CHARS = string.ascii_uppercase + string.digits


def _gen():
    return 'A-' + ''.join(secrets.choice(_CHARS) for _ in range(7))


def backfill_author_codes(apps, schema_editor):
    User = apps.get_model('users', 'User')
    used = set()
    # Only touches author accounts with no code yet — safe to re-run
    for user in User.objects.filter(role='author', author_code__isnull=True).order_by('id'):
        while True:
            code = _gen()
            if code not in used and not User.objects.filter(author_code=code).exists():
                used.add(code)
                break
        user.author_code = code
        user.save(update_fields=['author_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_authorkkyc_kyc_v2'),
    ]

    operations = [
        # ── 1. Add column (IF NOT EXISTS so a partial previous run is safe) ─────
        migrations.RunSQL(
            sql="ALTER TABLE users ADD COLUMN IF NOT EXISTS author_code VARCHAR(12) NULL;",
            reverse_sql="ALTER TABLE users DROP COLUMN IF EXISTS author_code;",
        ),
        # Sync Django migration state
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='user',
                    name='author_code',
                    field=models.CharField(
                        blank=True, null=True, max_length=12,
                        help_text='Unique public ID for author accounts (e.g. A-NLX4K8P).',
                    ),
                ),
            ],
        ),

        # ── 2. Backfill existing author accounts ─────────────────────────────────
        migrations.RunPython(backfill_author_codes, migrations.RunPython.noop),

        # ── 3. Add unique constraint + varchar_pattern_ops index ─────────────────
        migrations.RunSQL(
            sql=[
                # Unique constraint (skipped if it already exists)
                """
                DO $$ BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'users_user_author_code_uniq'
                          AND conrelid = 'users'::regclass
                    ) THEN
                        ALTER TABLE users
                            ADD CONSTRAINT users_user_author_code_uniq UNIQUE (author_code);
                    END IF;
                END $$;
                """,
                # LIKE index for prefix searches
                "CREATE INDEX IF NOT EXISTS users_author_code_like "
                "ON users USING btree (author_code varchar_pattern_ops);",
            ],
            reverse_sql=[
                "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_user_author_code_uniq;",
                "DROP INDEX IF EXISTS users_author_code_like;",
            ],
        ),
        # Sync Django migration state
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='user',
                    name='author_code',
                    field=models.CharField(
                        blank=True, null=True, db_index=True, max_length=12, unique=True,
                        help_text='Unique public ID for author accounts (e.g. A-NLX4K8P).',
                    ),
                ),
            ],
        ),
    ]
