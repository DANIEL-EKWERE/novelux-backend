"""Tidy existing chapter content into plain paragraphs (see html_clean).

    python manage.py clean_chapter_html --dry-run     # count what would change
    python manage.py clean_chapter_html               # rewrite them
    python manage.py clean_chapter_html --story <slug>

Only the content column is written (via .update), so chapter status, lock,
timestamps and editorial triggers are left alone.
"""
from django.core.management.base import BaseCommand

from apps.chapters.html_clean import clean_chapter_html
from apps.chapters.models import Chapter, count_words


class Command(BaseCommand):
    help = 'Normalise chapter HTML (editor <div> lines, pasted Google Docs/Word styles) to plain paragraphs.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--story', help='Only this story slug')

    def handle(self, *args, dry_run=False, story=None, **opts):
        qs = Chapter.objects.all()
        if story:
            qs = qs.filter(story__slug=story)
        changed = 0
        for pk, content in qs.values_list('pk', 'content').iterator():
            cleaned = clean_chapter_html(content)
            if cleaned == content:
                continue
            changed += 1
            if not dry_run:
                Chapter.objects.filter(pk=pk).update(content=cleaned, word_count=count_words(cleaned))
        verb = 'would change' if dry_run else 'cleaned'
        self.stdout.write(self.style.SUCCESS(f'{changed} chapter(s) {verb}.'))
