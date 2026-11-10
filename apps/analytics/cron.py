"""Scheduled jobs without a Celery worker.

Render's free plan can't run a worker or cron job, so celery beat never fires.
Instead, a free outside scheduler (e.g. cron-job.org) calls:

  GET /api/cron/run/?key=<CRON_SECRET>   every hour — runs whichever jobs are due
  GET /api/cron/ping/                    every 10 minutes — keeps the free
                                         service from going to sleep

Each job remembers when it last ran (ScheduledJobRun), so calling /run/ more
often than needed is harmless: a daily job still runs once a day. Two
overlapping calls can't run the same job twice — a job is claimed with a
conditional UPDATE before it runs.
"""
import hmac
import importlib
import logging
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import ScheduledJobRun

logger = logging.getLogger(__name__)

# (name, task path, run every N seconds) — mirrors CELERY_BEAT_SCHEDULE
JOBS = [
    ('expire_promotions',        'apps.editorial.tasks.expire_promotions',      3600),
    ('expire_bonus_coins',       'apps.coins.tasks.expire_bonus_coins',         3600),
    ('send_promotion_reminders', 'apps.editorial.tasks.send_promotion_reminders', 86400),
    ('vip_payout',               'apps.chapters.tasks.run_monthly_vip_payout',  86400),
    ('social_scheduled_posts',   'apps.social.tasks.publish_due_social_posts',  60),
    ('social_insights',          'apps.social.tasks.sync_social_insights',      3600),
]

GRACE = timedelta(minutes=5)  # an hourly call that's a little early still counts


def _authorised(request):
    secret = getattr(settings, 'CRON_SECRET', '')
    given = request.GET.get('key') or request.headers.get('X-Cron-Key', '')
    return bool(secret) and hmac.compare_digest(str(given), str(secret))


def _load(path):
    module, name = path.rsplit('.', 1)
    task = getattr(importlib.import_module(module), name)
    return getattr(task, 'run', task)  # call the task's code directly


def _claim(name, every):
    """Mark the job as started if it's due. True if this call should run it."""
    now = timezone.now()
    ScheduledJobRun.objects.get_or_create(name=name)
    # A call slightly early still counts — but never more than a quarter of
    # the interval, so a once-a-minute job can't run on every call
    grace = min(GRACE, timedelta(seconds=every / 4))
    due_before = now - timedelta(seconds=every) + grace
    from django.db.models import Q
    claimed = (ScheduledJobRun.objects
               .filter(name=name)
               .filter(Q(last_started__isnull=True) | Q(last_started__lte=due_before))
               .update(last_started=now))
    return claimed == 1


def run_due_jobs(only=None):
    results = {}
    for name, path, every in JOBS:
        if only and name not in only:
            continue
        if not _claim(name, every):
            results[name] = 'not due'
            continue
        ok, result = True, ''
        try:
            out = _load(path)()
            result = '' if out is None else str(out)[:500]
        except Exception as e:  # one job failing mustn't stop the others
            ok, result = False, f'{type(e).__name__}: {e}'[:500]
            logger.exception('Scheduled job %s failed', name)
        run = ScheduledJobRun.objects.get(name=name)
        run.last_finished, run.last_ok, run.last_result = timezone.now(), ok, result
        run.runs += 1
        run.save(update_fields=['last_finished', 'last_ok', 'last_result', 'runs'])
        results[name] = 'ok' if ok else f'failed — {result}'
    return results


@require_GET
def cron_run(request):
    """GET /api/cron/run/?key=… — run the jobs that are due."""
    if not getattr(settings, 'CRON_SECRET', ''):
        return JsonResponse({'detail': 'Scheduled jobs are switched off (CRON_SECRET not set).'}, status=503)
    if not _authorised(request):
        return JsonResponse({'detail': 'Forbidden.'}, status=403)
    only = [x for x in request.GET.get('only', '').split(',') if x]
    return JsonResponse({'ok': True, 'jobs': run_due_jobs(only or None)})


@require_GET
def cron_ping(request):
    """GET /api/cron/ping/ — cheap "are you awake" check (no database)."""
    return JsonResponse({'ok': True})
