"""Re-apply each story's "lock from chapter N" to all its chapters.

Chapters added or saved after a story's lock was set could end up unlocked
(the rule was only applied when the lock was changed). Chapter.save() now
enforces it; this repairs chapters that slipped through before the fix.
"""
from django.db import migrations


def reapply_locks(apps, schema_editor):
    Story = apps.get_model('stories', 'Story')
    Chapter = apps.get_model('chapters', 'Chapter')
    for story_id, lock_from in (Story.objects.filter(lock_from_chapter__isnull=False)
                                .values_list('id', 'lock_from_chapter')):
        Chapter.objects.filter(story_id=story_id, chapter_number__lt=lock_from).update(is_locked=False)
        Chapter.objects.filter(story_id=story_id, chapter_number__gte=lock_from).update(is_locked=True)


class Migration(migrations.Migration):

    dependencies = [
        ('chapters', '0011_chapterunlockearning'),
        ('stories', '0027_story_likes'),
    ]

    operations = [
        migrations.RunPython(reapply_locks, migrations.RunPython.noop),
    ]
