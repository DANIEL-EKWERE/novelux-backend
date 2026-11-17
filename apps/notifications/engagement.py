"""Scheduled pushes that bring readers back: check-in streaks, tasks / ad
rewards and "tired of ads? go VIP".

Runs every 15 minutes from the scheduled-jobs runner. Each reader gets at
most ONE of these a day, at a set hour in their local time (from the country
of their latest visit), and only if they've used the app recently. Several
wordings per kind rotate so the same message doesn't repeat.

All of them open the right screen when tapped: check-in, tasks and ad
rewards → Rewards ("screen": "rewards"), VIP → "screen": "vip".
"""
import logging
import random
from collections import defaultdict
from datetime import timedelta

from django.db.models import Exists, OuterRef, Q, Subquery
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_TZ = 'Africa/Lagos'

# (title, body) — {streak}, {coins}, {count}, {next_day} are filled in
CHECKIN_STREAK = [
    ("🔥 Don't break your {streak}-day streak", "Check in now for {coins} free coins before midnight."),
    ('Day {next_day} is waiting 🔥', "{streak} days in a row! Today's check-in is worth {coins} coins."),
    ('Your {coins} coins are ready 🪙', 'Tap to check in and keep your {streak}-day streak alive.'),
]
CHECKIN_NEW = [
    ('🪙 Free coins today', "Check in daily for up to 20 coins — today's reward is {coins}."),
    ('Daily check-in is open', 'Claim your free coins and start a new streak 🔥'),
    ('Coins for chapters 🪙', 'Check in once a day and collect free coins to unlock more chapters.'),
]
TASKS = [
    ('🎁 {count} rewards waiting', 'Finish quick tasks and earn up to {coins} free coins.'),
    ('Free coins inside 🪙', '{count} easy task{s} — up to {coins} coins to unlock more chapters.'),
    ('Unlock chapters for free 📖', 'Complete {count} task{s} in Rewards and collect up to {coins} coins.'),
]
ADS = [
    ('📺 Watch, earn, read', 'Watch a few short ads and earn up to {coins} bonus coins today.'),
    ('Low on coins? 🪙', 'Earn up to {coins} bonus coins today with short videos — then keep reading.'),
    ('Free coins, no purchase needed', "Today's ad rewards are worth up to {coins} bonus coins. Claim them in Rewards."),
]
VIP = [
    ('Tired of ads? 👑', 'Go VIP: read ad-free, download books for offline and enjoy the whole library.'),
    ('Read without interruptions 👑', 'VIP removes every ad. Try it and get lost in your story.'),
    ('Your next chapter, ad-free ✨', 'Upgrade to VIP for ad-free reading and offline downloads.'),
]


def _pick(variants, user_id, today, **ctx):
    """Rotate wording per reader and day (stable within a run)."""
    title, body = random.Random(f'{user_id}-{today}').choice(variants)
    return title.format(**ctx), body.format(**ctx)


def _local_hour(now, cc):
    import pytz
    tz = (pytz.country_timezones.get((cc or '').upper()) or [DEFAULT_TZ])[0]
    return now.astimezone(pytz.timezone(tz)).hour


def _candidates(now, s):
    """Active readers with a phone to push to, with their country and last visit."""
    from django.contrib.auth import get_user_model
    from apps.analytics.models import PageVisit
    from apps.users.models import FCMDevice
    from .models import EngagementPush, ReadingReminder
    User = get_user_model()
    visits = PageVisit.objects.filter(user=OuterRef('pk')).order_by('-created_at')
    return (User.objects.filter(is_active=True)
            .filter(Exists(FCMDevice.objects.filter(user=OuterRef('pk'), is_active=True)))
            .annotate(cc=Subquery(visits.exclude(country_code='').values('country_code')[:1]),
                      seen=Subquery(visits.values('created_at')[:1]))
            .filter(seen__gte=now - timedelta(days=s.active_days))
            # one of these a day…
            .exclude(Exists(EngagementPush.objects.filter(user=OuterRef('pk'),
                                                          sent_at__gte=now - timedelta(hours=20))))
            # …and not right after a "continue reading" reminder
            .exclude(Exists(ReadingReminder.objects.filter(user=OuterRef('pk'),
                                                           sent_at__gte=now - timedelta(hours=3))))
            .only('id', 'is_vip'))


def _last_sent(user_ids, kinds):
    from .models import EngagementPush
    out = {}
    for uid, at in (EngagementPush.objects.filter(user_id__in=user_ids, kind__in=kinds)
                    .order_by('sent_at').values_list('user_id', 'sent_at')):
        out[uid] = at
    return out


def _checkin_pushes(users, today):
    from apps.coins.models import STREAK_REWARDS, CheckinStreak
    streaks = {c.user_id: c for c in CheckinStreak.objects.filter(user__in=users)}
    out = []
    for u in users:
        st = streaks.get(u.pk)
        if st and st.last_checkin == today:
            continue                                   # already checked in
        alive = bool(st and st.current_streak and st.last_checkin == today - timedelta(days=1))
        streak = st.current_streak if alive else 0
        coins = STREAK_REWARDS[streak % len(STREAK_REWARDS)]
        variants = CHECKIN_STREAK if alive else CHECKIN_NEW
        out.append((u, 'checkin', *_pick(variants, u.pk, today, streak=streak, coins=coins,
                                         next_day=streak + 1), {'screen': 'rewards', 'section': 'checkin'}))
    return out


def _reward_pushes(users, today, now):
    """Tasks if there are any left to do, otherwise ad rewards."""
    from apps.coins.models import AdRewardTask, AdTaskProgress, Task, UserTask
    tasks = list(Task.objects.filter(is_active=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)))
    claimed = defaultdict(dict)
    for ut in UserTask.objects.filter(user__in=users, task__in=tasks, status=UserTask.STATUS_CLAIMED):
        claimed[ut.user_id][ut.task_id] = ut.claimed_at
    ad_tasks = list(AdRewardTask.objects.filter(is_active=True))
    ads_done = defaultdict(set)
    for uid, tid in AdTaskProgress.objects.filter(user__in=users, date=today, claimed_at__isnull=False) \
            .values_list('user_id', 'task_id'):
        ads_done[uid].add(tid)
    out = []
    for u in users:
        mine = claimed.get(u.pk, {})
        open_tasks = [t for t in tasks if t.pk not in mine or (
            t.is_repeatable and mine[t.pk] and mine[t.pk] + timedelta(hours=t.repeat_cooldown_hours) <= now)]
        ads_left = [t for t in ad_tasks if t.pk not in ads_done.get(u.pk, set())]
        if open_tasks:
            n = len(open_tasks)
            out.append((u, 'tasks', *_pick(TASKS, u.pk, today, count=n, s='' if n == 1 else 's',
                                           coins=sum(t.reward_coins for t in open_tasks)),
                        {'screen': 'rewards', 'section': 'tasks'}))
        elif ads_left:
            out.append((u, 'ads', *_pick(ADS, u.pk, today, coins=sum(t.reward_coins for t in ads_left)),
                        {'screen': 'rewards', 'section': 'ad_rewards'}))
    return out


def _vip_pushes(users, today):
    return [(u, 'vip', *_pick(VIP, u.pk, today), {'screen': 'vip'}) for u in users if not u.is_vip]


def _send(pushes, now):
    """Group identical messages so each goes out as one multicast."""
    from apps.users.models import FCMDevice
    from .fcm import send_to_tokens
    from .models import EngagementPush
    tokens = defaultdict(list)
    for uid, tok in FCMDevice.objects.filter(user__in=[p[0] for p in pushes], is_active=True) \
            .values_list('user_id', 'token'):
        tokens[uid].append(tok)
    groups = defaultdict(list)
    for user, kind, title, body, data in pushes:
        groups[(title, body, tuple(sorted(data.items())))].extend(tokens.get(user.pk, []))
    for (title, body, data), toks in groups.items():
        for i in range(0, len(toks), 500):
            try:
                send_to_tokens(toks[i:i + 500], title, body, dict(data))
            except Exception:
                logger.exception('Engagement push failed')
    EngagementPush.objects.bulk_create([EngagementPush(user=u, kind=k, title=t[:150], body=b[:255], sent_at=now)
                                        for u, k, t, b, _ in pushes])


def send_due(now=None):
    from .models import EngagementPushSettings
    s = EngagementPushSettings.get()
    now = now or timezone.now()
    today = now.date()      # check-ins use the server's (UTC) date
    by_hour = defaultdict(list)
    for u in _candidates(now, s):
        by_hour[_local_hour(now, u.cc)].append(u)

    pushes = []
    if s.rewards_enabled and by_hour.get(s.rewards_hour):
        users = by_hour[s.rewards_hour]
        last = _last_sent([u.pk for u in users], ['tasks', 'ads'])
        users = [u for u in users if not last.get(u.pk) or last[u.pk] <= now - timedelta(days=s.rewards_every_days)]
        pushes += _reward_pushes(users, today, now)
    if s.checkin_enabled and by_hour.get(s.checkin_hour):
        pushes += _checkin_pushes(by_hour[s.checkin_hour], today)
    if s.vip_enabled and by_hour.get(s.vip_hour):
        users = by_hour[s.vip_hour]
        last = _last_sent([u.pk for u in users], ['vip'])
        users = [u for u in users if not last.get(u.pk) or last[u.pk] <= now - timedelta(days=s.vip_every_days)]
        pushes += _vip_pushes(users, today)

    # Safety: one per reader per run even if two hours coincide in settings
    seen, unique = set(), []
    for p in pushes:
        if p[0].pk not in seen:
            seen.add(p[0].pk)
            unique.append(p)
    if unique:
        _send(unique, now)
    counts = defaultdict(int)
    for p in unique:
        counts[p[1]] += 1
    return ', '.join(f'{k}: {v}' for k, v in sorted(counts.items())) or 'no engagement pushes due'
