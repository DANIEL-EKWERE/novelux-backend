"""
Management command: fix_chapter_locks

For every story that currently has chapters locked from chapter 1 (the old default),
set lock_from_chapter=5 on the story and re-apply the locking so that chapters 1-4
become free and chapters 5+ remain locked.

Also handles stories with lock_from_chapter already set by re-applying the rule.

Usage:
    python manage.py fix_chapter_locks                # dry run
    python manage.py fix_chapter_locks --apply        # apply
    python manage.py fix_chapter_locks --apply --lock 5   # use a different lock chapter (default 5)
"""

from django.core.management.base import BaseCommand
from apps.stories.models import Story
from apps.chapters.models import Chapter, apply_lock_from_chapter


class Command(BaseCommand):
    help = 'Set lock_from_chapter=5 on stories where chapters are locked from ch.1, then re-apply locking.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Apply changes.')
        parser.add_argument('--lock', type=int, default=5, help='Chapter number to lock from (default: 5).')

    def handle(self, *args, **options):
        apply = options['apply']
        lock_from = options['lock']

        # Stories with no lock_from_chapter set and at least one locked chapter
        stories_needing_fix = Story.objects.filter(
            lock_from_chapter__isnull=True,
            chapters__is_locked=True,
        ).distinct().select_related('author')

        count = stories_needing_fix.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No stories need fixing.'))
        else:
            self.stdout.write(f'Found {count} stor{"y" if count == 1 else "ies"} with chapters locked but no lock_from_chapter set:')
            for s in stories_needing_fix[:20]:
                locked = Chapter.objects.filter(story=s, is_locked=True).count()
                self.stdout.write(f'  - [{s.pk}] "{s.title}" by {s.author.username} ({locked} locked chapters)')
            if count > 20:
                self.stdout.write(f'  ... and {count - 20} more')

        if not apply:
            self.stdout.write(self.style.WARNING(f'\nDry run. Re-run with --apply to set lock_from_chapter={lock_from} on these stories.'))
            return

        updated = 0
        for story in stories_needing_fix:
            story.lock_from_chapter = lock_from
            story.save(update_fields=['lock_from_chapter'])
            apply_lock_from_chapter(story)
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'\nUpdated {updated} stor{"y" if updated == 1 else "ies"}: lock_from_chapter={lock_from}, chapters re-locked.'))
