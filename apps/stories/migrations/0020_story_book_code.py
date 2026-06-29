import secrets
import string

from django.db import migrations, models

_CHARS = string.ascii_uppercase + string.digits


def _gen():
    return 'B-' + ''.join(secrets.choice(_CHARS) for _ in range(7))


def backfill_book_codes(apps, schema_editor):
    Story = apps.get_model('stories', 'Story')
    used = set()
    # Only touches rows that have no code yet — safe to re-run
    for story in Story.objects.filter(book_code='').order_by('id'):
        while True:
            code = _gen()
            if code not in used and not Story.objects.filter(book_code=code).exists():
                used.add(code)
                break
        story.book_code = code
        story.save(update_fields=['book_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0019_alter_tag_options_alter_story_subgenre_and_more'),
    ]

    operations = [
        # ── 1. Add column (IF NOT EXISTS so a partial previous run is safe) ─────
        migrations.RunSQL(
            sql="ALTER TABLE stories ADD COLUMN IF NOT EXISTS book_code VARCHAR(12) NOT NULL DEFAULT '';",
            reverse_sql="ALTER TABLE stories DROP COLUMN IF EXISTS book_code;",
        ),
        # Sync Django migration state (no DB work — column already added above)
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='story',
                    name='book_code',
                    field=models.CharField(
                        blank=True, default='', max_length=12,
                        help_text='Short unique code for searching this book (e.g. B-NLX4K8P).',
                    ),
                ),
            ],
        ),

        # ── 2. Backfill existing rows ────────────────────────────────────────────
        migrations.RunPython(backfill_book_codes, migrations.RunPython.noop),

        # ── 3. Add unique constraint + varchar_pattern_ops index ─────────────────
        #    Both use IF NOT EXISTS / conditional DDL so re-running is harmless.
        migrations.RunSQL(
            sql=[
                # Unique constraint (skipped if it already exists)
                """
                DO $$ BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'stories_story_book_code_uniq'
                          AND conrelid = 'stories'::regclass
                    ) THEN
                        ALTER TABLE stories
                            ADD CONSTRAINT stories_story_book_code_uniq UNIQUE (book_code);
                    END IF;
                END $$;
                """,
                # LIKE index for prefix searches (skipped if it already exists)
                "CREATE INDEX IF NOT EXISTS stories_book_code_efd5cf19_like "
                "ON stories USING btree (book_code varchar_pattern_ops);",
            ],
            reverse_sql=[
                "ALTER TABLE stories DROP CONSTRAINT IF EXISTS stories_story_book_code_uniq;",
                "DROP INDEX IF EXISTS stories_book_code_efd5cf19_like;",
            ],
        ),
        # Sync Django migration state to mark the field as unique + db_index
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='story',
                    name='book_code',
                    field=models.CharField(
                        blank=True, db_index=True, max_length=12, unique=True,
                        help_text='Short unique code for searching this book (e.g. B-NLX4K8P).',
                    ),
                ),
            ],
        ),
    ]
