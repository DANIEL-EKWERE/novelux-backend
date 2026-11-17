""""Continue reading" push: sent ~30 minutes after a reader stops mid-book.

record_reading() is called whenever a signed-in reader opens a chapter;
send_due() runs from the scheduled-jobs runner every few minutes.

Rules: one reminder per reading stop, at most one a day per reader, none in
the reader's quiet hours (sent when they end), only if a next chapter exists,
and never for stops older than 12 hours.
"""
import logging
from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_AGE = timedelta(hours=12)     # don't remind about reading from long ago
PER_RUN = 150                     # keeps one run well inside a request timeout
DEFAULT_TZ = 'Africa/Lagos'


def record_reading(user, chapter):
    from .models import ReadingReminder
    if not getattr(user, 'is_authenticated', False) or chapter.story.author_id == user.pk:
        return
    now = timezone.now()
    r = ReadingReminder.objects.filter(user=user).first()
    if r is None:
        ReadingReminder.objects.create(user=user, story_id=chapter.story_id,
                                       chapter_number=chapter.chapter_number, last_read_at=now)
        return
    came_back = bool(r.sent_at and r.sent_at > r.last_read_at and now - r.sent_at <= timedelta(hours=24))
    ReadingReminder.objects.filter(pk=r.pk).update(
        story_id=chapter.story_id, chapter_number=chapter.chapter_number, last_read_at=now,
        returned_count=F('returned_count') + (1 if came_back else 0))


def _timezones(user_ids):
    """Reader → time zone, from the country of their latest app/site visit."""
    import pytz
    from apps.analytics.models import PageVisit
    zones = {}
    rows = (PageVisit.objects.filter(user_id__in=user_ids).exclude(country_code='')
            .order_by('user_id', '-created_at').values_list('user_id', 'country_code'))
    for uid, cc in rows:
        if uid not in zones:
            tzs = pytz.country_timezones.get(cc.upper()) or [DEFAULT_TZ]
            zones[uid] = tzs[0]
    return zones


def _quiet(now, tz_name, start, end):
    import pytz
    try:
        hour = now.astimezone(pytz.timezone(tz_name)).hour
    except Exception:
        hour = now.astimezone(pytz.timezone(DEFAULT_TZ)).hour
    if start == end:
        return False
    return start <= hour or hour < end if start > end else start <= hour < end


def send_due(now=None):
    from apps.chapters.models import Chapter
    from .models import ReadingReminder, ReadingReminderSettings
    from .services import notify_user
    s = ReadingReminderSettings.get()
    if not s.enabled:
        return 'Continue-reading reminders are switched off'
    now = now or timezone.now()
    due = list(
        ReadingReminder.objects
        .filter(last_read_at__lte=now - timedelta(minutes=s.delay_minutes),
                last_read_at__gte=now - MAX_AGE,
                user__is_active=True, user__fcm_tokens__is_active=True)
        .filter(Q(handled_read_at__isnull=True) | Q(handled_read_at__lt=F('last_read_at')))
        .exclude(sent_at__gte=now - timedelta(hours=24))
        .select_related('story', 'user').distinct().order_by('last_read_at')[:PER_RUN])
    zones = _timezones([r.user_id for r in due])
    sent = 0
    for r in due:
        if _quiet(now, zones.get(r.user_id, DEFAULT_TZ), s.quiet_start_hour, s.quiet_end_hour):
            continue   # try again after quiet hours (if still within MAX_AGE)
        nxt = (Chapter.objects.filter(story=r.story, is_published=True, chapter_number__gt=r.chapter_number)
               .order_by('chapter_number').values_list('chapter_number', flat=True).first())
        fields = {'handled_read_at': r.last_read_at}
        if nxt and r.story.status != 'draft':
            ctx = {'story': r.story.title, 'chapter': nxt,
                   'name': r.user.first_name or r.user.username}
            try:
                notify_user(r.user, s.title.format(**ctx), s.body.format(**ctx),
                            data={'screen': 'story', 'slug': r.story.slug,
                                  'chapter_number': nxt, 'action': 'continue'})
                fields.update(sent_at=now, sent_count=F('sent_count') + 1)
                sent += 1
            except Exception:
                logger.exception('Continue-reading reminder failed for user %s', r.user_id)
        ReadingReminder.objects.filter(pk=r.pk).update(**fields)
    return f'{sent} continue-reading reminder(s) sent'
