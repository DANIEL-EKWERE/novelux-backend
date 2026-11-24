"""Daily retention pushes — up to 8 a day per reader, at set hours in their
local time (morning first), each one picked for that reader:

  continue      the book they're reading — the next chapter
  recommend     a popular book in the genre they read, that they haven't started
  new_arrivals  a fresh, popular book they haven't read
  trending      what everyone is reading
  checkin       today's check-in coins / don't break the streak
  tasks / ads   free coins in Rewards
  bonus_expiring  bonus coins about to vanish
  coins         coins sitting unused
  weekly        Monday morning "new week" hook
  vip           tired of ads? go VIP

Runs every 15 minutes from the scheduled-jobs runner. A reader gets at most
one per slot, never the same kind twice in a row, and each kind only a
couple of times a day. People without an account (guests) get the general
book pushes. Wording rotates so the same message rarely repeats.
"""
import logging
import random
from collections import defaultdict
from datetime import timedelta

from django.db.models import Exists, Max, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_TZ = 'Africa/Lagos'
SLOT_GAP = timedelta(minutes=50)          # never two pushes in the same slot

# Which kinds each slot prefers, in order (the first one that fits wins).
SLOT_PLAN = [
    ['weekly', 'checkin', 'continue', 'recommend', 'trending'],          # morning
    ['continue', 'recommend', 'trending'],
    ['tasks', 'ads', 'coins', 'recommend', 'trending'],                  # midday
    ['recommend', 'new_arrivals', 'continue', 'trending'],
    ['bonus_expiring', 'coins', 'continue', 'new_arrivals'],
    ['new_arrivals', 'recommend', 'continue', 'trending'],
    ['checkin', 'continue', 'vip', 'recommend'],                         # evening
    ['continue', 'vip', 'recommend', 'trending'],                        # night
]
PER_DAY = {'continue': 2, 'recommend': 2, 'checkin': 2, 'trending': 1, 'new_arrivals': 1, 'tasks': 1,
           'ads': 1, 'bonus_expiring': 1, 'coins': 1, 'weekly': 1, 'vip': 1}
GUEST_KINDS = {'recommend', 'new_arrivals', 'trending', 'weekly'}

# ── Wording (title, body) — {book} {chapter} {coins} {streak} {count} {genre}
T = {
    'continue': [
        ('📖 {book}', 'Chapter {chapter} is waiting. You stopped at the best part 👀'),
        ('You left them on a cliffhanger 😱', 'Chapter {chapter} of {book} — find out what happens next.'),
        ("Don't leave {book} hanging", 'Chapter {chapter} is just one tap away.'),
        ('🔥 Chapter {chapter} hits different', 'Pick up {book} right where you left off.'),
        ('Still thinking about {book}? 💭', 'So are we. Chapter {chapter} is ready.'),
        ('5 minutes? Perfect. ⏳', 'Just enough for chapter {chapter} of {book}.'),
    ],
    'recommend': [
        ('📚 Picked for you', '{book} — readers who love {genre} can\'t put this down.'),
        ('Your next obsession? 👀', '{book} is trending with {genre} fans right now.'),
        ('We found your type 😏', 'If you liked your last read, {book} will hook you from page one.'),
        ('💘 New crush unlocked', '{book}. Trust us on this one.'),
        ('Bored? Not for long.', 'Start {book} — chapter 1 is free.'),
    ],
    'new_arrivals': [
        ('✨ Fresh off the press', '{book} just landed. Be one of the first to read it.'),
        ('🆕 New on HuxNovel', '{book} — everyone will be talking about this soon.'),
        ('Hot new story alert 🔥', '{book} is climbing the charts. Start chapter 1 free.'),
    ],
    'trending': [
        ('🔥 Everyone is reading this', '{book} — see what the hype is about.'),
        ('📈 #1 right now', "{book} is today's most-read story. Don't miss out."),
        ('The story everyone\'s talking about 🗣️', 'Start {book} — chapter 1 is on us.'),
    ],
    'checkin_streak': [
        ("🔥 Don't break your {streak}-day streak", 'Check in now for {coins} free coins.'),
        ('🐾 Your check-in reward is escaping', 'Tap. Claim. Done. +{coins} coins.'),
        ('Day {next_day} is calling 📅', '{coins} free coins are waiting for you.'),
    ],
    'checkin_new': [
        ('🪙 Free coins today', "Today's check-in is worth {coins} coins. Tap to claim."),
        ("🐾 Don't let your check-in reward escape", 'Tap. Claim. Done.'),
        ('Your daily coins are ready 🎁', 'Check in and unlock more chapters for free.'),
    ],
    'tasks': [
        ('🎁 {count} rewards waiting', 'Finish quick tasks and earn up to {coins} free coins.'),
        ('Free coins inside 🪙', 'Easy tasks in Rewards — up to {coins} coins.'),
    ],
    'ads': [
        ('📺 Watch, earn, read', 'Short videos = up to {coins} bonus coins today.'),
        ('Low on coins? 🪙', 'Earn up to {coins} bonus coins with a few short videos.'),
    ],
    'bonus_expiring': [
        ('⏰ {coins} coins expire soon', "Use them before they vanish — they won't wait."),
        ('Your bonus coins are leaving 👋', '{coins} coins expire within a day. Spend them on a chapter now.'),
    ],
    'coins': [
        ('🪙 {coins} coins are just sitting there', 'We know you\'re busy, but your coins won\'t hear the excuse. Use them now.'),
        ('You have {coins} coins 💰', 'That\'s a few chapters on us. Go read!'),
        ('Coins don\'t read themselves 😅', 'You have {coins} — unlock your next chapter.'),
    ],
    'weekly': [
        ('📦 New week, new stuff', 'Click to see your haul.'),
        ('☀️ Fresh week, fresh stories', 'New chapters dropped while you were away.'),
        ('Monday mood: one more chapter 📖', "See what's new this week."),
    ],
    'vip': [
        ('Tired of ads? 👑', 'Go VIP: no ads, offline downloads and the whole library.'),
        ('Read without interruptions 👑', 'VIP removes every ad. Try it tonight.'),
        ('Your next chapter, ad-free ✨', 'Upgrade to VIP and binge in peace.'),
    ],
}


def _fmt(kind, key, seed, **ctx):
    title, body = random.Random(seed).choice(T[kind])
    return title.format(**ctx)[:150], body.format(**ctx)[:255]


def _zone(cc):
    import pytz
    return pytz.timezone((pytz.country_timezones.get((cc or '').upper()) or [DEFAULT_TZ])[0])


# ── Book pools (shared by everyone in a run) ──────────────────────────────────

def _book_pools(now):
    from apps.stories.models import Story
    from apps.stories.views import exclude_explicit
    live = exclude_explicit(Story.objects.exclude(status__in=['draft', 'rejected'])).filter(total_chapters__gt=0)
    trending = list(live.order_by('-total_views').values('id', 'slug', 'title', 'genre_id', 'genre__name')[:60])
    fresh = list(live.filter(created_at__gte=now - timedelta(days=21)).order_by('-total_views')
                 .values('id', 'slug', 'title', 'genre_id', 'genre__name')[:30])
    return trending, fresh


def _pick(pool, read, seed, genre=None):
    """A book from the pool they haven't read — same genre first."""
    options = [b for b in pool if b['id'] not in read]
    if genre:
        same = [b for b in options if b['genre_id'] == genre]
        options = same or options
    if not options:
        return None
    return random.Random(seed).choice(options[:8])


# ── Who is due ────────────────────────────────────────────────────────────────

def _users_due(now, s):
    from django.contrib.auth import get_user_model
    from apps.analytics.models import PageVisit
    from apps.users.models import FCMDevice
    User = get_user_model()
    visits = PageVisit.objects.filter(user=OuterRef('pk')).order_by('-created_at')
    qs = (User.objects.filter(is_active=True, is_banned=False)
          .filter(Exists(FCMDevice.objects.filter(user=OuterRef('pk'), is_active=True)))
          .annotate(cc=Subquery(visits.exclude(country_code='').values('country_code')[:1]),
                    seen=Coalesce(Subquery(visits.values('created_at')[:1]), 'date_joined'))
          .filter(seen__gte=now - timedelta(days=s.active_days)))
    return list(qs.only('id', 'is_vip', 'coin_balance', 'bonus_balance', 'first_name', 'username'))


def _slot_index(local_hour, slots):
    return slots.index(local_hour) if local_hour in slots else None


def send_due(now=None):
    from apps.users.models import FCMDevice
    from .fcm import send_personal
    from .models import EngagementPush, EngagementPushSettings, ReadingReminder
    s = EngagementPushSettings.get()
    now = now or timezone.now()
    slots = sorted({int(h) for h in (s.slot_hours or []) if 0 <= int(h) <= 23})[:max(s.daily_max, 0)]
    if not slots:
        return 'no slots set'

    # Readers whose local time is one of the slot hours
    batch = []                       # (user or None, token-for-guests, slot index, local datetime)
    for u in _users_due(now, s):
        local = now.astimezone(_zone(u.cc))
        i = _slot_index(local.hour, slots)
        if i is not None:
            batch.append((u, None, i, local))
    if s.guests_enabled:
        lagos = now.astimezone(_zone(''))
        i = _slot_index(lagos.hour, slots)
        if i is not None:
            for tok in (FCMDevice.objects.filter(user__isnull=True, is_active=True,
                                                 updated_at__gte=now - timedelta(days=s.active_days))
                        .values_list('token', flat=True)):
                batch.append((None, tok, i, lagos))
    if not batch:
        return 'no pushes due'

    users = [b[0] for b in batch if b[0]]
    uids = [u.pk for u in users]
    guest_toks = [b[1] for b in batch if b[1]]

    # What each one already got today (their local day)
    sent_today = defaultdict(list)
    recent = EngagementPush.objects.filter(sent_at__gte=now - timedelta(hours=26)).filter(
        Q(user_id__in=uids) | Q(device_token__in=guest_toks)).values_list('user_id', 'device_token', 'kind', 'sent_at')
    for uid, tok, kind, at in recent:
        sent_today[uid or tok].append((kind, at))
    vip_last = dict(EngagementPush.objects.filter(user_id__in=uids, kind='vip').values('user_id')
                    .annotate(t=Max('sent_at')).values_list('user_id', 't'))
    reminded = set(ReadingReminder.objects.filter(user_id__in=uids, sent_at__gte=now - SLOT_GAP)
                   .values_list('user_id', flat=True))

    ctx = _context(users, now)
    trending, fresh = _book_pools(now)

    pushes = []      # (user, token or None, kind, title, body, data)
    for user, tok, i, local in batch:
        key = user.pk if user else tok
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        today = [(k, at) for k, at in sent_today.get(key, []) if at >= midnight]
        if len(today) >= s.daily_max or any(at >= now - SLOT_GAP for _, at in today):
            continue
        if user and user.pk in reminded:
            continue
        counts = defaultdict(int)
        for k, _ in today:
            counts[k] += 1
        last_kind = max(today, key=lambda x: x[1])[0] if today else None
        seed = f'{key}-{local.date()}-{i}'
        choice = None
        for kind in SLOT_PLAN[min(i, len(SLOT_PLAN) - 1)] + ['recommend', 'trending']:
            if counts[kind] >= PER_DAY.get(kind, 1) or kind == last_kind:
                continue
            if user is None and kind not in GUEST_KINDS:
                continue
            msg = _make(kind, user, ctx, trending, fresh, local, seed, s, vip_last, now)
            if msg:
                choice = (kind, *msg)
                break
        if choice:
            pushes.append((user, tok, *choice))

    if not pushes:
        return 'no pushes due'
    tokens = defaultdict(list)
    for uid, t in FCMDevice.objects.filter(user_id__in=[p[0].pk for p in pushes if p[0]], is_active=True) \
            .values_list('user_id', 'token'):
        tokens[uid].append(t)
    items = []
    for user, tok, kind, title, body, data in pushes:
        for t in ([tok] if tok else tokens.get(user.pk, [])):
            items.append((t, title, body, data))
    sent, failed, dead = send_personal(items)
    if dead:
        FCMDevice.objects.filter(token__in=dead).update(is_active=False)
    EngagementPush.objects.bulk_create([EngagementPush(user=u, device_token=tok or '', kind=k, title=t, body=b,
                                                       sent_at=now) for u, tok, k, t, b, _ in pushes])
    by = defaultdict(int)
    for p in pushes:
        by[p[2]] += 1
    return f'{len(pushes)} retention push(es) — ' + ', '.join(f'{k}: {v}' for k, v in sorted(by.items())) + \
        (f' ({failed} failed)' if failed else '')


# ── Per-reader facts, loaded in bulk ──────────────────────────────────────────

def _context(users, now):
    from apps.chapters.models import Chapter
    from apps.coins.models import AdRewardTask, AdTaskProgress, CheckinStreak, ReadingHistory, Task, UserTask
    from apps.users.models import BonusGrant
    from .models import ReadingReminder
    uids = [u.pk for u in users]
    c = {'reading': {}, 'read': defaultdict(set), 'streak': {}, 'bonus_exp': {}, 'tasks': {}, 'ads_left': {}}
    if not uids:
        return c
    # The book each is reading: server record first, then the app's history
    for r in ReadingReminder.objects.filter(user_id__in=uids).values('user_id', 'story_id', 'chapter_number', 'last_read_at'):
        c['reading'][r['user_id']] = (r['story_id'], r['chapter_number'], r['last_read_at'])
    for h in ReadingHistory.objects.filter(user_id__in=uids).values('user_id', 'story_id', 'chapter_number', 'read_at'):
        c['read'][h['user_id']].add(h['story_id'])
        cur = c['reading'].get(h['user_id'])
        if cur is None or (h['read_at'] and cur[2] and h['read_at'] > cur[2]):
            c['reading'][h['user_id']] = (h['story_id'], h['chapter_number'], h['read_at'])
    story_ids = {v[0] for v in c['reading'].values()}
    from apps.stories.models import Story
    stories = {s['id']: s for s in Story.objects.filter(pk__in=story_ids).exclude(status__in=['draft', 'rejected'])
               .exclude(author__is_banned=True).values('id', 'slug', 'title', 'genre_id', 'genre__name')}
    last_ch = dict(Chapter.objects.filter(story_id__in=story_ids, is_published=True).values('story_id')
                   .annotate(m=Max('chapter_number')).values_list('story_id', 'm'))
    c['stories'], c['last_ch'] = stories, last_ch
    c['streak'] = {st.user_id: st for st in CheckinStreak.objects.filter(user_id__in=uids)}
    for uid, amt in (BonusGrant.objects.filter(user_id__in=uids, remaining__gt=0, expires_at__gt=now,
                                               expires_at__lte=now + timedelta(hours=48))
                     .values('user_id').annotate(a=Max('remaining')).values_list('user_id', 'a')):
        c['bonus_exp'][uid] = amt
    tasks = list(Task.objects.filter(is_active=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)))
    done = defaultdict(set)
    for uid, tid in UserTask.objects.filter(user_id__in=uids, status='claimed', task__is_repeatable=False) \
            .values_list('user_id', 'task_id'):
        done[uid].add(tid)
    for uid in uids:
        left = [t for t in tasks if t.pk not in done[uid]]
        if left:
            c['tasks'][uid] = (len(left), sum(t.reward_coins for t in left))
    ad_tasks = list(AdRewardTask.objects.filter(is_active=True))
    ads_done = defaultdict(set)
    for uid, tid in AdTaskProgress.objects.filter(user_id__in=uids, date=now.date(), claimed_at__isnull=False) \
            .values_list('user_id', 'task_id'):
        ads_done[uid].add(tid)
    for uid in uids:
        left = [t for t in ad_tasks if t.pk not in ads_done[uid]]
        if left:
            c['ads_left'][uid] = sum(t.reward_coins for t in left)
    return c


def _book_data(b):
    return {'screen': 'story', 'slug': b['slug']}


def _make(kind, user, c, trending, fresh, local, seed, s, vip_last, now):
    """(title, body, data) for this reader, or None when it doesn't fit."""
    from apps.coins.models import STREAK_REWARDS
    uid = user.pk if user else None
    read = c['read'].get(uid, set()) if user else set()
    reading = c['reading'].get(uid) if user else None
    if kind == 'continue' and s.books_enabled and reading:
        story = c['stories'].get(reading[0])
        if story and c['last_ch'].get(story['id'], 0) > reading[1]:
            t, b = _fmt('continue', None, seed, book=story['title'], chapter=reading[1] + 1)
            return t, b, {**_book_data(story), 'chapter_number': reading[1] + 1, 'action': 'continue'}
        return None
    if kind == 'recommend' and s.books_enabled:
        genre = c['stories'].get(reading[0], {}).get('genre_id') if reading else None
        b = _pick(trending, read, seed, genre)
        if b:
            t, body = _fmt('recommend', None, seed, book=b['title'], genre=(b['genre__name'] or 'great stories'))
            return t, body, _book_data(b)
        return None
    if kind == 'new_arrivals' and s.books_enabled:
        b = _pick(fresh, read, seed)
        return (*_fmt('new_arrivals', None, seed, book=b['title']), _book_data(b)) if b else None
    if kind == 'trending' and s.books_enabled:
        b = _pick(trending[:10], read, seed)
        return (*_fmt('trending', None, seed, book=b['title']), _book_data(b)) if b else None
    if kind == 'weekly':
        if local.weekday() != 0:
            return None
        b = _pick(fresh or trending, read, seed)
        return (*_fmt('weekly', None, seed), _book_data(b) if b else {'screen': 'rewards'})
    if user is None:
        return None
    if kind == 'checkin' and s.checkin_enabled:
        st = c['streak'].get(uid)
        if st and st.last_checkin == now.date():
            return None
        alive = bool(st and st.current_streak and st.last_checkin == now.date() - timedelta(days=1))
        streak = st.current_streak if alive else 0
        coins = STREAK_REWARDS[streak % len(STREAK_REWARDS)]
        t, b = _fmt('checkin_streak' if alive else 'checkin_new', None, seed,
                    streak=streak, coins=coins, next_day=streak + 1)
        return t, b, {'screen': 'rewards', 'section': 'checkin'}
    if kind == 'tasks' and s.rewards_enabled and uid in c['tasks']:
        n, coins = c['tasks'][uid]
        return (*_fmt('tasks', None, seed, count=n, coins=coins), {'screen': 'rewards', 'section': 'tasks'})
    if kind == 'ads' and s.rewards_enabled and c['ads_left'].get(uid):
        return (*_fmt('ads', None, seed, coins=c['ads_left'][uid]), {'screen': 'rewards', 'section': 'ad_rewards'})
    if kind == 'bonus_expiring' and s.coins_enabled and c['bonus_exp'].get(uid):
        return (*_fmt('bonus_expiring', None, seed, coins=c['bonus_exp'][uid]), _coins_target(c, uid, reading))
    if kind == 'coins' and s.coins_enabled:
        total = (user.coin_balance or 0) + (user.bonus_balance or 0)
        if total >= 20:
            return (*_fmt('coins', None, seed, coins=total), _coins_target(c, uid, reading))
        return None
    if kind == 'vip' and s.vip_enabled and not user.is_vip:
        last = vip_last.get(uid)
        if last and last > now - timedelta(days=s.vip_every_days):
            return None
        return (*_fmt('vip', None, seed), {'screen': 'vip'})
    return None


def _coins_target(c, uid, reading):
    """Coins pushes open the book they're reading (to spend them), else Rewards."""
    story = c['stories'].get(reading[0]) if reading else None
    return _book_data(story) if story else {'screen': 'rewards'}
