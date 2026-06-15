from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.stories.models import Story

PROMO_FIELDS = [
    ('is_editors_pick',     'editors_pick_expires_at'),
    ('is_world_famous',     'world_famous_expires_at'),
    ('is_african_folktale', 'african_folktale_expires_at'),
    ('is_featured',         'featured_expires_at'),
    ('is_free_download',    'free_download_expires_at'),
]


class Command(BaseCommand):
    help = 'Clear expired CE promotion flags from stories'

    def handle(self, *args, **options):
        now = timezone.now()
        total = 0
        for bool_field, expiry_field in PROMO_FIELDS:
            qs = Story.objects.filter(**{
                bool_field: True,
                f'{expiry_field}__isnull': False,
                f'{expiry_field}__lte': now,
            })
            count = qs.count()
            if count:
                qs.update(**{bool_field: False, expiry_field: None})
                total += count
                self.stdout.write(f'  Cleared {count} expired {bool_field}')
        self.stdout.write(self.style.SUCCESS(f'Done — {total} promotion(s) expired.'))
