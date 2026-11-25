"""The Promotion team's shelves and scheduled placements.

A Shelf is a row of books in the app (Featured, Trending, an Explore tab
section…) with a number of slots. A Placement puts one book in one slot of a
shelf between two times. The app shows a shelf's live placements first, in
slot order, then fills the rest with its usual books — so preparing Monday's
10 books and Tuesday's 10 books in advance makes the shelf switch by itself.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

# Shelves in the app that the team controls: key → (name, where, default slots)
HOME_SHELVES = [
    ('featured',      'Featured Books',     'Home', 10),
    ('trending',      'Trending Books',     'Home', 10),
    ('editors-pick',  "Editor's Picks",     'Home', 10),
    ('recommended',   'Recommended Reads',  'Home', 10),
    ('new-arrivals',  'New & Rising',       'Home', 10),
    ('ranking',       'Rankings',           'Home', 10),
    ('short-stories', 'Short Stories',      'Home', 10),
]


class Shelf(models.Model):
    key       = models.CharField(max_length=80, unique=True)
    name      = models.CharField(max_length=120)
    group     = models.CharField(max_length=40, default='Home', help_text='Home, or the Explore tab it sits in.')
    capacity  = models.PositiveSmallIntegerField(default=10, help_text='How many books the team can place.')
    is_active = models.BooleanField(default=True)
    order     = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'promotion_shelves'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.group} → {self.name}'

    @classmethod
    def ensure_defaults(cls):
        """Create any missing shelf: home rows + every Explore tab section."""
        from apps.editorial.views import TAB_SECTIONS
        have = set(cls.objects.values_list('key', flat=True))
        new, n = [], 0
        for key, name, group, cap in HOME_SHELVES:
            n += 1
            if key not in have:
                new.append(cls(key=key, name=name, group=group, capacity=cap, order=n))
        for tab, sections in TAB_SECTIONS.items():
            for s in sections:
                n += 1
                key = f'explore:{tab}:{s["slug"]}'
                if key not in have:
                    new.append(cls(key=key, name=s['name'], group=f'Explore · {tab.replace("-", " ").title()}',
                                   capacity=5, order=n))
        if new:
            cls.objects.bulk_create(new, ignore_conflicts=True)


class Placement(models.Model):
    SOURCE_TEAM, SOURCE_REQUEST, SOURCE_CE = 'team', 'se_request', 'ce'
    SOURCES = [(SOURCE_TEAM, 'Promotion team'), (SOURCE_REQUEST, 'SE request'), (SOURCE_CE, 'Chief editor')]

    shelf      = models.ForeignKey(Shelf, on_delete=models.CASCADE, related_name='placements')
    story      = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='shelf_placements')
    position   = models.PositiveSmallIntegerField(default=1, help_text='Slot number (1 = first).')
    starts_at  = models.DateTimeField(db_index=True)
    ends_at    = models.DateTimeField(null=True, blank=True, db_index=True, help_text='Blank = until removed.')
    paused     = models.BooleanField(default=False)
    cancelled  = models.BooleanField(default=False)
    label      = models.CharField(max_length=80, blank=True, help_text='Set name, e.g. "Monday set".')
    note       = models.CharField(max_length=255, blank=True)
    source     = models.CharField(max_length=12, choices=SOURCES, default=SOURCE_TEAM)
    request    = models.ForeignKey('editorial.SEPromotionRequest', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='placements')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promotion_placements'
        ordering = ['starts_at', 'position']

    def status(self, now=None):
        now = now or timezone.now()
        if self.cancelled:
            return 'cancelled'
        if self.ends_at and self.ends_at <= now:
            return 'expired'
        if self.starts_at > now:
            return 'scheduled'
        return 'paused' if self.paused else 'active'


def live_story_ids(shelf_key, now=None):
    """Story ids on a shelf right now, in slot order (capped at its slots)."""
    from django.db.models import Q
    now = now or timezone.now()
    shelf = Shelf.objects.filter(key=shelf_key, is_active=True).first()
    if not shelf:
        return []
    rows = (Placement.objects.filter(shelf=shelf, cancelled=False, paused=False, starts_at__lte=now)
            .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
            .order_by('position', '-starts_at').values_list('story_id', flat=True))
    out = []
    for sid in rows:
        if sid not in out:
            out.append(sid)
    return out[:shelf.capacity]


class PromotionLog(models.Model):
    """Every promotion decision, for the team's history."""
    ACTIONS = [('scheduled', 'Scheduled books'), ('rotation', 'Planned a daily rotation'),
               ('edited', 'Changed a placement'), ('cancelled', 'Cancelled a placement'),
               ('reordered', 'Reordered a shelf'), ('shelf_updated', 'Changed a shelf'),
               ('request_approved', 'Approved an SE request'), ('request_rejected', 'Rejected an SE request'),
               ('task_sent', 'Sent an author promotion task'), ('task_updated', 'Updated an author task')]
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    action     = models.CharField(max_length=20, choices=ACTIONS)
    shelf      = models.ForeignKey(Shelf, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    story      = models.ForeignKey('stories.Story', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    note       = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'promotion_log'
        ordering = ['-created_at']


class PromotionTask(models.Model):
    """An offer the Promotion team sends an author: meet these requirements
    (e.g. 2 chapters a day for 7 days) and the book gets this promotion."""
    STATUS = [('sent', 'Waiting for the author'), ('accepted', 'Accepted — in progress'), ('declined', 'Declined'),
              ('met', 'Requirements met'), ('missed', 'Requirements missed'), ('qualified', 'Qualified — promoted'),
              ('cancelled', 'Cancelled')]
    story            = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='promotion_tasks')
    author           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promotion_tasks')
    title            = models.CharField(max_length=150)
    message          = models.TextField(help_text='Congratulations / offer text the author reads.')
    chapters_per_day = models.PositiveSmallIntegerField(default=1)
    duration_days    = models.PositiveSmallIntegerField(default=7, help_text='How many days the requirement runs.')
    reward           = models.CharField(max_length=255, help_text='The promotion or opportunity on offer.')
    promotion_start  = models.DateField(null=True, blank=True)
    respond_by       = models.DateTimeField(null=True, blank=True, help_text='Accept before this, or the offer lapses.')
    conditions       = models.TextField(blank=True)
    status           = models.CharField(max_length=10, choices=STATUS, default='sent', db_index=True)
    accepted_at      = models.DateTimeField(null=True, blank=True)
    responded_at     = models.DateTimeField(null=True, blank=True)
    decline_reason   = models.CharField(max_length=255, blank=True)
    created_by       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promotion_tasks'
        ordering = ['-created_at']

    def window(self):
        """The requirement runs from acceptance for `duration_days` days."""
        from datetime import timedelta
        if not self.accepted_at:
            return None, None
        return self.accepted_at, self.accepted_at + timedelta(days=self.duration_days)

    def progress(self, now=None):
        """Chapters uploaded each day of the window vs the daily requirement."""
        from datetime import timedelta
        from apps.chapters.models import Chapter
        now = now or timezone.now()
        start, end = self.window()
        if not start:
            return {'days': [], 'uploaded': 0, 'required': self.chapters_per_day * self.duration_days,
                    'days_met': 0, 'days_elapsed': 0, 'on_track': None}
        stamps = list(Chapter.objects.filter(story=self.story, created_at__gte=start, created_at__lt=end)
                      .exclude(status__in=['draft', 'rejected']).values_list('created_at', flat=True))
        days = []
        for i in range(self.duration_days):
            a, b = start + timedelta(days=i), start + timedelta(days=i + 1)
            n = sum(1 for t in stamps if a <= t < b)
            state = 'future' if a > now else ('met' if n >= self.chapters_per_day else ('today' if b > now else 'missed'))
            days.append({'day': i + 1, 'date': timezone.localtime(a).date().isoformat(), 'chapters': n, 'state': state})
        elapsed = [d for d in days if d['state'] in ('met', 'missed')]
        return {'days': days, 'uploaded': len(stamps), 'required': self.chapters_per_day * self.duration_days,
                'days_met': sum(1 for d in days if d['state'] == 'met'), 'days_elapsed': len(elapsed),
                'on_track': not any(d['state'] == 'missed' for d in days), 'ends_at': end.isoformat()}

    def refresh_status(self, now=None):
        """Accepted tasks become met / missed as the days pass."""
        now = now or timezone.now()
        if self.status == 'sent' and self.respond_by and self.respond_by < now:
            self.status = 'cancelled'
            self.save(update_fields=['status'])
        if self.status != 'accepted':
            return
        p = self.progress(now)
        if not p['on_track']:
            self.status = 'missed'
        elif p['days_met'] == self.duration_days:
            self.status = 'met'
        else:
            return
        self.save(update_fields=['status'])


class SearchLog(models.Model):
    """What readers search for (to spot books people look for but don't read)."""
    query      = models.CharField(max_length=120, db_index=True)
    results    = models.PositiveIntegerField(default=0)
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'search_log'
