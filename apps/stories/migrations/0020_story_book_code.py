import secrets
import string

from django.db import migrations, models

_CHARS = string.ascii_uppercase + string.digits


def _gen():
    return 'B-' + ''.join(secrets.choice(_CHARS) for _ in range(7))


def backfill_book_codes(apps, schema_editor):
    Story = apps.get_model('stories', 'Story')
    used = set()
    for story in Story.objects.filter(book_code='').order_by('id'):
        while True:
            code = _gen()
            if code not in used and not Story.objects.filter(book_code=code).exists():
                used.add(code)
                break
        story.book_code = code
        story.save(update_fields=['book_code'])


def add_like_index(apps, schema_editor):
    db = schema_editor.connection.vendor
    if db == 'postgresql':
        schema_editor.execute(
            "CREATE INDEX IF NOT EXISTS stories_book_code_efd5cf19_like "
            "ON stories USING btree (book_code varchar_pattern_ops);"
        )


def drop_like_index(apps, schema_editor):
    db = schema_editor.connection.vendor
    if db == 'postgresql':
        schema_editor.execute(
            "DROP INDEX IF EXISTS stories_book_code_efd5cf19_like;"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0019_alter_tag_options_alter_story_subgenre_and_more'),
    ]

    operations = [
        # 1. Add column
        migrations.AddField(
            model_name='story',
            name='book_code',
            field=models.CharField(
                blank=True, default='', max_length=12,
                help_text='Short unique code for searching this book (e.g. B-NLX4K8P).',
            ),
        ),

        # 2. Backfill existing rows
        migrations.RunPython(backfill_book_codes, migrations.RunPython.noop),

        # 3. Add unique constraint + db_index
        migrations.AlterField(
            model_name='story',
            name='book_code',
            field=models.CharField(
                blank=True, db_index=True, max_length=12, unique=True,
                help_text='Short unique code for searching this book (e.g. B-NLX4K8P).',
            ),
        ),

        # 4. PostgreSQL-only: varchar_pattern_ops index for prefix LIKE searches
        migrations.RunPython(add_like_index, drop_like_index),
    ]
