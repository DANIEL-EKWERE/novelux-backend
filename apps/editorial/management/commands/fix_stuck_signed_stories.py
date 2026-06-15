"""
Management command: fix_stuck_signed_stories

Finds all stories with contract_status='signed' but status='draft' and sets them
to status='ongoing'. Run this once in production to repair stories that signed a
contract before the accept_contract view was updated to set status='ongoing' immediately.

Usage:
    python manage.py fix_stuck_signed_stories          # dry run (shows what would change)
    python manage.py fix_stuck_signed_stories --apply  # apply the fix
"""

from django.core.management.base import BaseCommand
from apps.stories.models import Story


class Command(BaseCommand):
    help = 'Fix signed stories stuck in draft status — sets them to ongoing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Apply the fix. Without this flag the command runs as a dry run.',
        )

    def handle(self, *args, **options):
        apply = options['apply']

        stuck = Story.objects.filter(contract_status='signed', status='draft').select_related('author')
        count = stuck.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No stuck stories found.'))
            return

        self.stdout.write(f'Found {count} signed stor{"y" if count == 1 else "ies"} stuck in draft:')
        for s in stuck:
            self.stdout.write(f'  - [{s.pk}] "{s.title}" by {s.author.username}')

        if not apply:
            self.stdout.write(self.style.WARNING('\nDry run — no changes made. Re-run with --apply to fix.'))
            return

        updated = stuck.update(status='ongoing')
        self.stdout.write(self.style.SUCCESS(f'\nUpdated {updated} stor{"y" if updated == 1 else "ies"} to ongoing.'))
