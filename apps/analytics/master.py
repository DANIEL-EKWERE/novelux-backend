"""Master dashboard API — the owner's view of everything.

Built from data the platform already records:
  * PageVisit — every website and app API request (path, IP, GeoIP country /
    city, device, browser, OS, user). This is the activity / location /
    "is online" feed.
  * Users, devices, purchases, subscriptions, coins, reading history,
    unlocks, tips, comments, ratings, follows …
  * The editorial trail — SE/CE reviews, contract applications, KYC, earnings
    approvals, promotions, invites.

Every endpoint is admin-only (superuser or role "admin").
"""
import re
from collections import Counter, defaultdict
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import (
    Count, Max, Min, OuterRef, Q, Subquery, Sum,
)
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import PageVisit

User = get_user_model()

ONLINE_MINUTES = 5


class IsMaster(BasePermission):
    message = 'Master dashboard is for admins only.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.role == 'admin'))


# ── helpers ───────────────────────────────────────────────────────────────────

def _days(request, default=30):
    try:
        d = int(request.query_params.get('days', default))
    except (TypeError, ValueError):
        d = default
    return max(1, min(d, 365))


def _iso(dt):
    return dt.isoformat() if dt else None


def _usd(v):
    return float(v or 0)


def _series(rows, start, days, key='d', val='n'):
    """[{d, n}] → dense list over every day of the period."""
    by_day = {str(r[key]): r[val] for r in rows}
    out = []
    for i in range(days + 1):
        day = (start + timedelta(days=i)).date()
        if day > timezone.localdate():
            break
        v = by_day.get(str(day), 0)
        out.append({'date': str(day), 'value': float(v) if v is not None else 0})
    return out


def _avatar(request, u):
    try:
        return request.build_absolute_uri(u.avatar.url) if u.avatar else None
    except Exception:
        return None


def _user_brief(request, u, extra=None):
    d = {
        'id': u.pk, 'username': u.username, 'email': u.email,
        'name': u.get_full_name(), 'role': u.role, 'avatar': _avatar(request, u),
        'date_joined': _iso(u.date_joined), 'last_login': _iso(u.last_login),
        'is_vip': u.is_vip, 'is_banned': u.is_banned, 'is_active': u.is_active,
        'is_superuser': u.is_superuser,
    }
    if extra:
        d.update(extra)
    return d


# Turn request paths into readable activity
_ACTIVITY = [
    (r'^/api/chapters/([^/]+)/chapters/(\d+)/unlock/?$', 'Unlocked chapter {1} of {0}'),
    (r'^/api/chapters/([^/]+)/chapters/(\d+)/ad-access/?$', 'Watched an ad to read chapter {1} of {0}'),
    (r'^/api/chapters/([^/]+)/chapters/download/?$', 'Opened download for {0}'),
    (r'^/api/chapters/([^/]+)/chapters/(\d+)/?$', 'Read chapter {1} of {0}'),
    (r'^/api/chapters/([^/]+)/chapters/?$', 'Viewed chapter list of {0}'),
    (r'^/api/stories/reviews/', 'Viewed / wrote reviews'),
    (r'^/api/stories/([^/]+)/apply-contract/?$', 'Applied for a contract ({0})'),
    (r'^/api/stories/(?:search|trending|featured|recommended)', 'Browsed / searched stories'),
    (r'^/api/stories/([^/]+)/?$', 'Opened book page: {0}'),
    (r'^/api/stories/', 'Browsed stories'),
    (r'^/api/coins/checkin', 'Daily check-in'),
    (r'^/api/coins/(?:rewards|claim|tasks|ad-tasks)', 'Rewards / tasks'),
    (r'^/api/coins/', 'Coins & store'),
    (r'^/api/tips/', 'Gifts / tips'),
    (r'^/api/comments/', 'Comments'),
    (r'^/api/audio/', 'Audio / listening'),
    (r'^/api/notifications/', 'Notifications'),
    (r'^/api/auth/(?:login|token|social)', 'Signed in'),
    (r'^/api/auth/register', 'Signed up'),
    (r'^/api/auth/me', 'Opened the app'),
    (r'^/api/auth/', 'Account'),
    (r'^/api/users/', 'Profiles / follows'),
    (r'^/api/reading/', 'Reading time sync'),
    (r'^/api/editorial/', 'Editorial dashboard'),
    (r'^/api/blog/', 'Blog'),
    (r'^/api/', 'App activity'),
    (r'^/explore/([^/]+)', 'Website: book page {0}'),
    (r'^/story/([^/]+)', 'Website: story {0}'),
    (r'^/editorial/se', 'Website: SE dashboard'),
    (r'^/editorial/ce', 'Website: CE dashboard'),
    (r'^/author', 'Website: author dashboard'),
    (r'^/master', 'Website: master dashboard'),
    (r'^/$', 'Website: home page'),
    (r'^/', 'Website: {path}'),
]
_ACTIVITY = [(re.compile(p), label) for p, label in _ACTIVITY]


def describe(path):
    for rx, label in _ACTIVITY:
        m = rx.search(path or '')
        if m:
            try:
                return label.format(*[g.replace('-', ' ') for g in m.groups()], path=path)
            except (IndexError, KeyError):
                return label
    return path


_NORM = [
    (re.compile(r'/\d+(?=/|$)'), '/<n>'),
    (re.compile(r'^(/api/(?:chapters|stories|audio)/)(?!search|trending|featured|recommended|mine|genres)[^/]+'), r'\1<slug>'),
    (re.compile(r'^(/(?:explore|story)/)[^/]+'), r'\1<slug>'),
]


def _normalise(path):
    for rx, rep in _NORM:
        path = rx.sub(rep, path)
    return path


def _platform(os_name, device_type):
    o = (os_name or '').lower()
    if 'android' in o:
        return 'Android'
    if 'ios' in o or 'iphone' in o or 'ipad' in o:
        return 'iOS'
    if device_type in ('desktop',):
        return 'Web (desktop)'
    if device_type:
        return 'Web (mobile)'
    return 'Unknown'


# Opening a chapter: GET /api/chapters/<slug>/chapters/<n>/ (not unlock / ad
# access). ReadingHistory keeps only one row per reader per book, so chapter
# reads are counted from the request log instead.
CHAPTER_OPEN = r'^/api/chapters/[^/]+/chapters/[0-9]+/?$'
_CHAPTER_SLUG = re.compile(r'^/api/chapters/([^/]+)/chapters/[0-9]+/?$')


def _chapter_opens_by_slug(visits):
    """{story slug: chapter opens} from a PageVisit queryset."""
    out = Counter()
    for path, n in visits.filter(path__regex=CHAPTER_OPEN).values_list('path').annotate(n=Count('id')):
        m = _CHAPTER_SLUG.match(path)
        if m:
            out[m.group(1)] += n
    return out


# ── Overview ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsMaster])
def overview(request):
    """GET /api/master/overview/?days=30 — the headline numbers and trends."""
    from apps.coins.models import Purchase
    from apps.chapters.models import Chapter, ChapterUnlock
    from apps.coins.models import ReadingHistory
    from apps.stories.models import Story
    from apps.tips.models import Tip

    days = _days(request)
    now = timezone.now()
    start = now - timedelta(days=days)
    start_day = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    pv = PageVisit.objects.filter(created_at__gte=start)

    def active_users(since):
        return (PageVisit.objects.filter(created_at__gte=since, user__isnull=False)
                .values('user').distinct().count())

    dau, wau, mau = active_users(now - timedelta(days=1)), active_users(now - timedelta(days=7)), active_users(now - timedelta(days=30))
    online_since = now - timedelta(minutes=ONLINE_MINUTES)
    online = active_users(online_since)
    online_guests = (PageVisit.objects.filter(created_at__gte=online_since, user__isnull=True)
                     .values('ip_address').distinct().count())

    purchases = Purchase.objects.filter(status=Purchase.STATUS_COMPLETED, completed_at__gte=start)
    rev = purchases.aggregate(total=Sum('amount_paid_usd'), n=Count('id'))
    gifts = Tip.objects.filter(status=Tip.STATUS_COMPLETED, created_at__gte=start, amount_usd__isnull=False) \
        .aggregate(total=Sum('amount_usd'), n=Count('id'))
    paying_users = purchases.values('user').distinct().count()

    roles = dict(User.objects.values_list('role').annotate(n=Count('id')))
    new_users = User.objects.filter(date_joined__gte=start)
    vip_active = User.objects.filter(is_vip=True).filter(Q(vip_expires__isnull=True) | Q(vip_expires__gt=now)).count()

    # Trends
    active_rows = (pv.filter(user__isnull=False).annotate(d=TruncDate('created_at'))
                   .values('d').annotate(n=Count('user', distinct=True)))
    visitor_rows = pv.annotate(d=TruncDate('created_at')).values('d').annotate(n=Count('ip_address', distinct=True))
    signup_rows = new_users.annotate(d=TruncDate('date_joined')).values('d').annotate(n=Count('id'))
    revenue_rows = purchases.annotate(d=TruncDate('completed_at')).values('d').annotate(n=Sum('amount_paid_usd'))
    read_rows = (pv.filter(path__regex=CHAPTER_OPEN).annotate(d=TruncDate('created_at'))
                 .values('d').annotate(n=Count('id')))

    # Audience
    countries = list(pv.exclude(country='').values('country')
                     .annotate(country_code=Max('country_code'), users=Count('user', distinct=True),
                               visitors=Count('ip_address', distinct=True))
                     .order_by('-visitors')[:15])
    cities = list(pv.exclude(city='').values('city', 'country')
                  .annotate(visitors=Count('ip_address', distinct=True)).order_by('-visitors')[:15])
    platforms = Counter()
    for r in pv.values('os', 'device_type').annotate(n=Count('ip_address', distinct=True)):
        platforms[_platform(r['os'], r['device_type'])] += r['n']
    browsers = list(pv.exclude(browser='').values('browser').annotate(n=Count('id')).order_by('-n')[:8])

    # Funnel for people who joined in the period
    joined_ids = new_users.values('id')
    funnel = {
        'signed_up': new_users.count(),
        'read_a_chapter': ReadingHistory.objects.filter(user_id__in=joined_ids).values('user').distinct().count(),
        'unlocked_a_chapter': ChapterUnlock.objects.filter(user_id__in=joined_ids).values('user').distinct().count(),
        'made_a_purchase': Purchase.objects.filter(user_id__in=joined_ids, status=Purchase.STATUS_COMPLETED)
                                   .values('user').distinct().count(),
    }

    opens = _chapter_opens_by_slug(pv)
    readers = dict(ReadingHistory.objects.filter(read_at__gte=start).values('story__slug')
                   .annotate(n=Count('user', distinct=True)).values_list('story__slug', 'n'))
    titles = dict(Story.objects.filter(slug__in=set(opens) | set(readers)).values_list('slug', 'title'))
    top_books = sorted(
        [{'story__slug': slug, 'story__title': titles.get(slug, slug),
          'reads': opens.get(slug, 0), 'readers': readers.get(slug, 0)} for slug in titles],
        key=lambda b: (b['reads'], b['readers']), reverse=True)[:10]

    return Response({
        'days': days,
        'kpis': {
            'users_total': User.objects.count(),
            'new_users': new_users.count(),
            'online_now': online, 'online_guests': online_guests,
            'dau': dau, 'wau': wau, 'mau': mau,
            'stickiness': round(dau / mau, 3) if mau else 0,
            'visitors': pv.values('ip_address').distinct().count(),
            'revenue_usd': _usd(rev['total']), 'purchases': rev['n'],
            'gifts_usd': _usd(gifts['total']), 'gifts': gifts['n'],
            'paying_users': paying_users,
            'arppu': round(_usd(rev['total']) / paying_users, 2) if paying_users else 0,
            'vip_active': vip_active,
            'readers': roles.get('reader', 0), 'authors': roles.get('author', 0),
            'editors': roles.get('se', 0) + roles.get('ce', 0),
            'books': Story.objects.count(),
            'new_books': Story.objects.filter(created_at__gte=start).count(),
            'chapters_published': Chapter.objects.filter(is_published=True, updated_at__gte=start).count(),
            'chapter_reads': pv.filter(path__regex=CHAPTER_OPEN).count(),
            'unlocks': ChapterUnlock.objects.filter(created_at__gte=start).count(),
            'banned': User.objects.filter(is_banned=True).count(),
        },
        'trends': {
            'active_users': _series(active_rows, start_day, days),
            'visitors': _series(visitor_rows, start_day, days),
            'signups': _series(signup_rows, start_day, days),
            'revenue': _series(revenue_rows, start_day, days),
            'reads': _series(read_rows, start_day, days),
        },
        'countries': countries,
        'cities': cities,
        'platforms': [{'name': k, 'value': v} for k, v in platforms.most_common()],
        'browsers': browsers,
        'funnel': funnel,
        'top_books': top_books,
    })


# ── Realtime ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsMaster])
def realtime(request):
    """GET /api/master/realtime/ — who's on right now (last 30 minutes)."""
    now = timezone.now()
    since = now - timedelta(minutes=30)
    recent = PageVisit.objects.filter(created_at__gte=since)

    per_minute = Counter()
    for t, uid, ip in recent.values_list('created_at', 'user_id', 'ip_address'):
        per_minute[(int((now - t).total_seconds() // 60), uid or ip)] += 1
    minutes = [0] * 30
    for (m, _who) in per_minute:
        if 0 <= m < 30:
            minutes[29 - m] += 1

    online_since = now - timedelta(minutes=ONLINE_MINUTES)
    last = (PageVisit.objects.filter(created_at__gte=online_since, user__isnull=False)
            .values('user').annotate(last=Max('created_at'), hits=Count('id')).order_by('-last')[:100])
    users = {u.pk: u for u in User.objects.filter(pk__in=[r['user'] for r in last])}
    latest_visit = {}
    for v in (PageVisit.objects.filter(created_at__gte=online_since, user_id__in=list(users))
              .order_by('-created_at').values('user_id', 'path', 'city', 'country', 'country_code',
                                              'os', 'device_type')):
        latest_visit.setdefault(v['user_id'], v)
    online = []
    for r in last:
        u = users.get(r['user'])
        if not u:
            continue
        v = latest_visit.get(u.pk, {})
        online.append(_user_brief(request, u, {
            'last_seen': _iso(r['last']), 'hits': r['hits'],
            'doing': describe(v.get('path')), 'city': v.get('city', ''), 'country': v.get('country', ''),
            'country_code': v.get('country_code', ''), 'platform': _platform(v.get('os'), v.get('device_type')),
        }))

    stream = [{
        'at': _iso(v.created_at), 'user_id': v.user_id,
        'username': v.user.username if v.user_id else None,
        'doing': describe(v.path), 'path': v.path,
        'city': v.city, 'country': v.country, 'country_code': v.country_code,
        'platform': _platform(v.os, v.device_type), 'ip': v.ip_address,
    } for v in recent.select_related('user').order_by('-created_at')[:80]]

    countries = list(recent.exclude(country='').values('country')
                     .annotate(country_code=Max('country_code'), n=Count('ip_address', distinct=True))
                     .order_by('-n')[:10])

    return Response({
        'online_users': len(online),
        'online_guests': PageVisit.objects.filter(created_at__gte=online_since, user__isnull=True)
                                  .values('ip_address').distinct().count(),
        'last_30_min': {'users': recent.filter(user__isnull=False).values('user').distinct().count(),
                        'visitors': recent.values('ip_address').distinct().count(),
                        'per_minute': minutes},
        'online': online, 'stream': stream, 'countries': countries,
    })


# ── Users ─────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsMaster])
def users(request):
    """GET /api/master/users/?q=&role=&status=online|active7|dormant|vip|banned|paying
                              &country=&sort=last_seen|joined|coins|spent&page=1"""
    from apps.coins.models import Purchase
    from apps.users.models import UserDevice

    p = request.query_params
    now = timezone.now()
    qs = User.objects.all()
    if p.get('q'):
        q = p['q'].strip()
        cond = Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        if q.isdigit():
            cond |= Q(pk=int(q))
        qs = qs.filter(cond)
    if p.get('role'):
        qs = qs.filter(role=p['role'])
    status = p.get('status')
    if status == 'online':
        qs = qs.filter(pk__in=PageVisit.objects.filter(
            created_at__gte=now - timedelta(minutes=ONLINE_MINUTES), user__isnull=False).values('user'))
    elif status == 'active7':
        qs = qs.filter(pk__in=PageVisit.objects.filter(
            created_at__gte=now - timedelta(days=7), user__isnull=False).values('user'))
    elif status == 'dormant':
        qs = qs.exclude(pk__in=PageVisit.objects.filter(
            created_at__gte=now - timedelta(days=30), user__isnull=False).values('user'))
    elif status == 'vip':
        qs = qs.filter(is_vip=True)
    elif status == 'banned':
        qs = qs.filter(is_banned=True)
    elif status == 'paying':
        qs = qs.filter(pk__in=Purchase.objects.filter(status=Purchase.STATUS_COMPLETED).values('user'))
    if p.get('country'):
        qs = qs.filter(pk__in=PageVisit.objects.filter(country=p['country'], user__isnull=False).values('user'))

    last_pv = PageVisit.objects.filter(user=OuterRef('pk')).order_by('-created_at')
    last_geo = PageVisit.objects.filter(user=OuterRef('pk')).exclude(country='').order_by('-created_at')
    qs = qs.annotate(
        last_seen=Subquery(last_pv.values('created_at')[:1]),
        last_path=Subquery(last_pv.values('path')[:1]),
        country=Subquery(last_geo.values('country')[:1]),
        country_code=Subquery(last_geo.values('country_code')[:1]),
        city=Subquery(last_geo.values('city')[:1]),
        last_os=Subquery(last_pv.values('os')[:1]),
        last_device=Subquery(last_pv.values('device_type')[:1]),
        spent=Subquery(Purchase.objects.filter(user=OuterRef('pk'), status=Purchase.STATUS_COMPLETED)
                       .values('user').annotate(t=Sum('amount_paid_usd')).values('t')[:1]),
    )
    from django.db.models import F
    sort = p.get('sort', 'last_seen')
    if sort == 'joined':
        qs = qs.order_by('-date_joined')
    elif sort == 'coins':
        qs = qs.order_by('-coin_balance', '-date_joined')
    elif sort == 'spent':
        qs = qs.order_by(F('spent').desc(nulls_last=True), '-date_joined')
    else:
        qs = qs.order_by(F('last_seen').desc(nulls_last=True), '-date_joined')

    try:
        page = max(1, int(p.get('page', 1)))
    except ValueError:
        page = 1
    size = 50
    total = qs.count()
    rows = list(qs[(page - 1) * size: page * size])
    platforms = {}
    for uid, plat in UserDevice.objects.filter(user_id__in=[u.pk for u in rows]).values_list('user_id', 'platform'):
        platforms.setdefault(uid, plat)
    online_cut = now - timedelta(minutes=ONLINE_MINUTES)
    return Response({
        'total': total, 'page': page, 'pages': (total + size - 1) // size,
        'results': [_user_brief(request, u, {
            'last_seen': _iso(u.last_seen),
            'online': bool(u.last_seen and u.last_seen >= online_cut),
            'doing': describe(u.last_path) if u.last_path else '',
            'country': u.country or '', 'country_code': u.country_code or '', 'city': u.city or '',
            'platform': {'ios': 'iOS', 'android': 'Android'}.get((platforms.get(u.pk) or '').lower())
                        or _platform(u.last_os, u.last_device),
            'coins': u.coin_balance, 'bonus': u.bonus_balance, 'spent_usd': _usd(u.spent),
        }) for u in rows],
    })


def _sessions(times, gap_minutes=30):
    """Visits → sessions (a new session after 30 idle minutes)."""
    sessions = []
    for t in sorted(times):
        if sessions and (t - sessions[-1][1]).total_seconds() <= gap_minutes * 60:
            sessions[-1][1] = t
            sessions[-1][2] += 1
        else:
            sessions.append([t, t, 1])
    return sessions


@api_view(['GET'])
@permission_classes([IsMaster])
def user_detail(request, user_id):
    """GET /api/master/users/<id>/ — everything about one person."""
    from apps.chapters.models import ChapterUnlock, ChapterUnlockEarning
    from apps.coins.models import (CheckinStreak, DailyRewardClaim, Purchase, ReadingHistory,
                                   ReadingSession, Subscription, UserTask)
    from apps.comments.models import Comment
    from apps.stories.models import Bookmark, Rating, ReadingProgress, Story, StoryLike
    from apps.tips.models import Tip
    from apps.users.models import (BonusGrant, CoinTransaction, FCMDevice, Follow, UserDevice)

    u = get_object_or_404(User, pk=user_id)
    now = timezone.now()
    visits = PageVisit.objects.filter(user=u)
    last_visit = visits.order_by('-created_at').first()

    # Activity
    timeline = [{
        'at': _iso(v.created_at), 'doing': describe(v.path), 'path': v.path,
        'city': v.city, 'country': v.country, 'ip': v.ip_address,
        'platform': _platform(v.os, v.device_type), 'browser': v.browser,
    } for v in visits.order_by('-created_at')[:300]]
    since90 = now - timedelta(days=90)
    heat = [[0] * 24 for _ in range(7)]
    for r in (visits.filter(created_at__gte=since90).annotate(wd=ExtractWeekDay('created_at'),
                                                            h=ExtractHour('created_at'))
              .values('wd', 'h').annotate(n=Count('id'))):
        heat[(r['wd'] - 1) % 7][r['h']] = r['n']  # 0 = Sunday
    times = list(visits.filter(created_at__gte=now - timedelta(days=30))
                 .order_by('-created_at').values_list('created_at', flat=True)[:20000])
    sess = _sessions(times)
    daily = (visits.filter(created_at__gte=now - timedelta(days=30)).annotate(d=TruncDate('created_at'))
             .values('d').annotate(n=Count('id')))
    start_day = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Where and on what
    locations = list(visits.exclude(country='').values('country', 'country_code', 'city')
                     .annotate(hits=Count('id'), first=Min('created_at'), last=Max('created_at'))
                     .order_by('-last')[:30])
    ips = list(visits.exclude(ip_address__isnull=True).values('ip_address', 'country', 'city')
               .annotate(hits=Count('id'), last=Max('created_at')).order_by('-last')[:30])
    ip_list = [r['ip_address'] for r in ips] + ([u.registration_ip] if u.registration_ip else [])
    shared = (User.objects.filter(Q(registration_ip__in=ip_list) |
                                  Q(pk__in=PageVisit.objects.filter(ip_address__in=ip_list[:10])
                                    .exclude(user=u).values('user')))
              .exclude(pk=u.pk).distinct()[:25])
    tech = list(visits.values('os', 'browser', 'device_type').annotate(hits=Count('id'), last=Max('created_at'))
                .order_by('-last')[:10])

    # Money
    purchases = Purchase.objects.filter(user=u).select_related('coin_package', 'subscription_plan')
    paid = purchases.filter(status=Purchase.STATUS_COMPLETED).aggregate(t=Sum('amount_paid_usd'), n=Count('id'))
    sub = Subscription.objects.filter(user=u).select_related('plan').first()

    # Reading
    history = list(ReadingHistory.objects.filter(user=u).select_related('story').order_by('-read_at')[:50])
    progress = list(ReadingProgress.objects.filter(user=u).select_related('story').order_by('-updated_at')[:30])
    minutes = ReadingSession.objects.filter(user=u).aggregate(
        total=Sum('minutes'), d30=Sum('minutes', filter=Q(date__gte=(now - timedelta(days=30)).date())))
    unlocks = ChapterUnlock.objects.filter(user=u).aggregate(n=Count('id'), coins=Sum('coins_spent'))

    data = {
        'profile': _user_brief(request, u, {
            'bio': u.bio, 'date_of_birth': str(u.date_of_birth) if u.date_of_birth else None,
            'registration_ip': u.registration_ip, 'ban_reason': u.ban_reason,
            'preferred_language': u.preferred_language, 'preferred_genres': u.preferred_genres,
            'reading_level': u.reading_level, 'reading_xp': u.reading_xp,
            'total_chapters_read': u.total_chapters_read,
            'restricted_mode': u.restricted_mode_enabled,
            'vip_expires': _iso(u.vip_expires), 'ad_free_expires': _iso(u.ad_free_expires),
            'is_superuser': u.is_superuser, 'author_code': u.author_code, 'editor_code': u.editor_code,
        }),
        'status': {
            'online': bool(last_visit and last_visit.created_at >= now - timedelta(minutes=ONLINE_MINUTES)),
            'last_seen': _iso(last_visit.created_at) if last_visit else None,
            'last_doing': describe(last_visit.path) if last_visit else '',
            'first_seen': _iso(visits.aggregate(m=Min('created_at'))['m']),
            'total_hits': visits.count(),
            'active_days_30': len({t.date() for t in times}),
            'sessions_30': len(sess),
            'avg_session_minutes': round(sum((e - s).total_seconds() for s, e, _ in sess) / 60 / len(sess), 1) if sess else 0,
        },
        'activity': {
            'timeline': timeline,
            'heatmap': heat,
            'daily': _series(daily, start_day, 30),
            'sessions': [{'start': _iso(s), 'end': _iso(e), 'hits': n,
                          'minutes': round((e - s).total_seconds() / 60, 1)}
                         for s, e, n in sorted(sess, key=lambda x: x[0], reverse=True)[:30]],
        },
        'location': {
            'current': {'country': last_visit.country, 'city': last_visit.city,
                        'country_code': last_visit.country_code} if last_visit else None,
            'places': [{**r, 'first': _iso(r['first']), 'last': _iso(r['last'])} for r in locations],
            'ips': [{**r, 'last': _iso(r['last'])} for r in ips],
            'shared_accounts': [_user_brief(request, x) for x in shared],
        },
        'devices': {
            'devices': [{'device_id': d.device_id, 'platform': d.platform, 'first_seen': _iso(d.first_seen),
                         'last_seen': _iso(d.last_seen)} for d in UserDevice.objects.filter(user=u)],
            'app_installs': [{'platform': f.platform, 'model': f.device_model, 'app_version': f.app_version,
                              'active': f.is_active, 'updated_at': _iso(f.updated_at)}
                             for f in FCMDevice.objects.filter(user=u)[:10]],
            'browsers_os': [{**t, 'last': _iso(t['last'])} for t in tech],
        },
        'wallet': {
            'coins': u.coin_balance, 'bonus': u.bonus_balance,
            'spent_usd': _usd(paid['t']), 'purchases': paid['n'],
            'subscription': {'plan': str(sub.plan) if sub and sub.plan else None,
                             'active': sub.is_active, 'started_at': _iso(sub.started_at),
                             'expires_at': _iso(sub.expires_at), 'auto_renew': sub.auto_renew} if sub else None,
            'purchase_list': [{'at': _iso(x.completed_at or x.created_at), 'type': x.get_purchase_type_display(),
                               'item': str(x.coin_package or x.subscription_plan or ''), 'usd': _usd(x.amount_paid_usd),
                               'coins': x.coins_granted, 'status': x.status,
                               'store': 'App store' if x.iap_transaction_id else ('Card' if x.stripe_payment_id or x.stripe_session_id else '—')}
                              for x in purchases[:40]],
            'transactions': [{'at': _iso(t.created_at), 'type': t.transaction_type, 'amount': t.amount,
                              'reason': t.reason, 'balance_after': t.balance_after}
                             for t in CoinTransaction.objects.filter(user=u)[:60]],
            'bonus_grants': [{'at': _iso(g.created_at), 'reason': g.reason, 'amount': g.amount,
                              'remaining': g.remaining, 'expires_at': _iso(g.expires_at)}
                             for g in BonusGrant.objects.filter(user=u).order_by('-created_at')[:30]],
        },
        'reading': {
            'minutes_total': minutes['total'] or 0, 'minutes_30': minutes['d30'] or 0,
            'unlocks': unlocks['n'], 'unlock_coins': unlocks['coins'] or 0,
            'history': [{'at': _iso(h.read_at), 'story': h.story.title if h.story_id else '',
                         'slug': h.story.slug if h.story_id else '', 'chapter': h.chapter_number,
                         'chapter_title': h.chapter_title} for h in history],
            'library': [{'story': r.story.title, 'slug': r.story.slug, 'last_chapter': r.last_chapter,
                         'updated_at': _iso(r.updated_at)} for r in progress],
        },
        'engagement': {
            'comments': Comment.objects.filter(user=u).count(),
            'ratings': Rating.objects.filter(user=u).count(),
            'likes': StoryLike.objects.filter(user=u).count(),
            'bookmarks': Bookmark.objects.filter(user=u).count(),
            'following': Follow.objects.filter(follower=u).count(),
            'followers': Follow.objects.filter(following=u).count(),
            'gifts_sent': Tip.objects.filter(sender=u, status=Tip.STATUS_COMPLETED).count(),
            'reward_claims': DailyRewardClaim.objects.filter(user=u).count(),
            'tasks_done': UserTask.objects.filter(user=u, status__in=['completed', 'claimed']).count(),
            'checkin_streak': CheckinStreak.objects.filter(user=u).values(
                'current_streak', 'longest_streak', 'total_checkins', 'last_checkin').first(),
            'recent_comments': [{'at': _iso(c.created_at), 'story': c.story.title if c.story_id else '',
                                 'text': c.content[:200]}
                                for c in Comment.objects.filter(user=u).select_related('story').order_by('-created_at')[:15]],
        },
    }

    if u.role == 'author' or Story.objects.filter(author=u).exists():
        from apps.users.models import AuthorKYC, AuthorProfile
        profile = AuthorProfile.objects.filter(user=u).first()
        kyc = AuthorKYC.objects.filter(user=u).first()
        try:
            link = u.editor_link
        except Exception:
            link = None
        earn = ChapterUnlockEarning.objects.filter(author=u).aggregate(
            held=Sum('coins', filter=Q(status='held')), released=Sum('coins', filter=Q(status='released')))
        data['author'] = {
            'pen_name': profile.pen_name if profile else '',
            'has_contract': profile.has_contract if profile else False,
            'contract_signed_at': _iso(profile.contract_signed_at) if profile else None,
            'kyc': kyc.status if kyc else 'not_submitted',
            'editor': link.assigned_se.username if link and link.assigned_se else None,
            'editor_id': link.assigned_se_id if link else None,
            'earnings_coins_held': earn['held'] or 0, 'earnings_coins_released': earn['released'] or 0,
            'gifts_received_usd': _usd(Tip.objects.filter(recipient=u, status=Tip.STATUS_COMPLETED)
                                       .aggregate(t=Sum('amount_usd'))['t']),
            'books': [{'title': s.title, 'slug': s.slug, 'status': s.status, 'contract_status': s.contract_status,
                       'chapters': s.total_chapters, 'views': s.total_views, 'unlocks': s.total_unlocks,
                       'words': s.word_count, 'created_at': _iso(s.created_at), 'updated_at': _iso(s.updated_at)}
                      for s in Story.objects.filter(author=u).order_by('-updated_at')],
        }
    if u.role in ('se', 'ce'):
        data['editor'] = _editor_stats(u, now - timedelta(days=30))
    return Response(data)


# ── Team ──────────────────────────────────────────────────────────────────────

def _editor_stats(ed, since):
    from apps.chapters.models import Chapter, ChapterEditRequest, ChapterUnlockEarning
    from apps.editorial.models import (AuthorEditorLink, AuthorWarning, ContractApplication, EditorInvite,
                                       EditorialNote, SEPromotionRequest, StoryPromotion)
    from apps.tips.models import Tip
    from apps.users.models import AuthorKYC

    apps_qs = ContractApplication.objects.filter(assigned_se=ed)
    return {
        'authors': AuthorEditorLink.objects.filter(assigned_se=ed).count(),
        'new_authors': AuthorEditorLink.objects.filter(assigned_se=ed, assigned_at__gte=since).count(),
        'chapters_reviewed': Chapter.objects.filter(reviewed_by_se=ed).count(),
        'chapters_reviewed_period': Chapter.objects.filter(reviewed_by_se=ed, reviewed_at__gte=since).count(),
        'edits_reviewed': ChapterEditRequest.objects.filter(reviewed_by=ed).count(),
        'applications': apps_qs.count(),
        'applications_pending': apps_qs.filter(status__in=['pending', 'se_reviewing']).count(),
        'applications_approved': apps_qs.filter(status__in=['se_approved', 'contract_sent', 'signed']).count(),
        'applications_rejected': apps_qs.filter(status='rejected').count(),
        'contracts_sent': apps_qs.filter(contract_sent_at__isnull=False).count(),
        'contracts_signed': apps_qs.filter(status='signed').count(),
        'contracts_signed_period': apps_qs.filter(signed_at__gte=since).count(),
        'ce_signed': ContractApplication.objects.filter(ce_signed_by=ed).count(),
        'kyc_reviewed': AuthorKYC.objects.filter(reviewed_by=ed).count(),
        'earnings_approved': (ChapterUnlockEarning.objects.filter(released_by=ed).count()
                              + Tip.objects.filter(earning_reviewed_by=ed).count()),
        'promotion_requests': SEPromotionRequest.objects.filter(se=ed).count(),
        'promotions': StoryPromotion.objects.filter(se=ed).count(),
        'invites_sent': EditorInvite.objects.filter(invited_by=ed).count(),
        'warnings_issued': AuthorWarning.objects.filter(issued_by=ed).count(),
        'notes_written': EditorialNote.objects.filter(written_by=ed).count(),
    }


@api_view(['GET'])
@permission_classes([IsMaster])
def team(request):
    """GET /api/master/team/?days=30 — every SE and CE and how they're doing."""
    from apps.editorial.models import EditorAssignment

    days = _days(request)
    now = timezone.now()
    since = now - timedelta(days=days)
    start_day = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    editors = list(User.objects.filter(role__in=['se', 'ce']).order_by('role', 'username'))
    ids = [e.pk for e in editors]
    last_seen = dict(PageVisit.objects.filter(user_id__in=ids).values('user')
                     .annotate(m=Max('created_at')).values_list('user', 'm'))
    activity = defaultdict(list)
    for r in (PageVisit.objects.filter(user_id__in=ids, created_at__gte=since)
              .annotate(d=TruncDate('created_at')).values('user', 'd').annotate(n=Count('id'))):
        activity[r['user']].append(r)
    supervisors = dict(EditorAssignment.objects.filter(editor_id__in=ids)
                       .values_list('editor_id', 'supervisor__username'))
    out = []
    for e in editors:
        seen = last_seen.get(e.pk)
        out.append(_user_brief(request, e, {
            'last_seen': _iso(seen),
            'online': bool(seen and seen >= now - timedelta(minutes=ONLINE_MINUTES)),
            'supervisor': supervisors.get(e.pk),
            'active_days': len(activity[e.pk]),
            'activity': _series(activity[e.pk], start_day, days),
            'stats': _editor_stats(e, since),
        }))
    return Response({'days': days, 'editors': out})


@api_view(['GET'])
@permission_classes([IsMaster])
def team_member(request, editor_id):
    """GET /api/master/team/<id>/ — one editor: their authors, books and a
    timeline of what they've done."""
    from apps.chapters.models import Chapter, ChapterEditRequest, ChapterUnlockEarning
    from apps.editorial.models import AuthorEditorLink, ContractApplication, SEPromotionRequest
    from apps.stories.models import Story
    from apps.users.models import AuthorKYC, AuthorProfile

    ed = get_object_or_404(User, pk=editor_id, role__in=['se', 'ce'])
    now = timezone.now()
    links = list(AuthorEditorLink.objects.filter(assigned_se=ed).select_related('author'))
    author_ids = [l.author_id for l in links]
    seen = dict(PageVisit.objects.filter(user_id__in=author_ids).values('user')
                .annotate(m=Max('created_at')).values_list('user', 'm'))
    pens = dict(AuthorProfile.objects.filter(user_id__in=author_ids).values_list('user_id', 'pen_name'))
    kyc = dict(AuthorKYC.objects.filter(user_id__in=author_ids).values_list('user_id', 'status'))
    books = defaultdict(list)
    for s in Story.objects.filter(author_id__in=author_ids).order_by('-updated_at'):
        books[s.author_id].append({'title': s.title, 'slug': s.slug, 'status': s.status,
                                   'contract_status': s.contract_status, 'chapters': s.total_chapters,
                                   'views': s.total_views, 'updated_at': _iso(s.updated_at)})
    authors = [_user_brief(request, l.author, {
        'pen_name': pens.get(l.author_id, ''), 'kyc': kyc.get(l.author_id, 'not_submitted'),
        'linked_at': _iso(l.assigned_at), 'link_method': l.link_method,
        'last_seen': _iso(seen.get(l.author_id)), 'books': books.get(l.author_id, []),
    }) for l in links]
    authors.sort(key=lambda a: a['last_seen'] or '', reverse=True)

    # What they've done, newest first
    log = []
    for c in Chapter.objects.filter(reviewed_by_se=ed, reviewed_at__isnull=False).select_related('story') \
            .order_by('-reviewed_at')[:60]:
        log.append({'at': c.reviewed_at, 'what': f'Reviewed chapter {c.chapter_number} of "{c.story.title}" ({c.status})'})
    for r in ChapterEditRequest.objects.filter(reviewed_by=ed, reviewed_at__isnull=False) \
            .select_related('chapter__story').order_by('-reviewed_at')[:40]:
        log.append({'at': r.reviewed_at, 'what': f'{r.status.title()} an edit to "{r.chapter.story.title}" ch. {r.chapter.chapter_number}'})
    for a in ContractApplication.objects.filter(Q(assigned_se=ed) | Q(ce_signed_by=ed)).select_related('story'):
        if a.se_reviewed_at and a.assigned_se_id == ed.pk:
            log.append({'at': a.se_reviewed_at, 'what': f'Reviewed contract application for "{a.story.title}"'})
        if a.contract_sent_at:
            log.append({'at': a.contract_sent_at, 'what': f'Contract sent for "{a.story.title}"'})
        if a.signed_at:
            log.append({'at': a.signed_at, 'what': f'Contract signed: "{a.story.title}"'})
        if a.rejected_at:
            log.append({'at': a.rejected_at, 'what': f'Application rejected: "{a.story.title}"'})
    for k in AuthorKYC.objects.filter(reviewed_by=ed, reviewed_at__isnull=False).select_related('user') \
            .order_by('-reviewed_at')[:40]:
        log.append({'at': k.reviewed_at, 'what': f'KYC {k.status} for {k.user.username}'})
    for e in ChapterUnlockEarning.objects.filter(released_by=ed, released_at__isnull=False) \
            .select_related('author').order_by('-released_at')[:40]:
        log.append({'at': e.released_at, 'what': f'{e.status.title()} {e.coins}-coin earning for {e.author.username}'})
    for pr in SEPromotionRequest.objects.filter(se=ed).select_related('story').order_by('-created_at')[:30]:
        log.append({'at': pr.created_at, 'what': f'Asked to promote "{pr.story.title}" ({pr.status})'})
    for v in PageVisit.objects.filter(user=ed).order_by('-created_at')[:1]:
        log.append({'at': v.created_at, 'what': 'Last seen: ' + describe(v.path)})
    log.sort(key=lambda x: x['at'], reverse=True)

    return Response({
        'editor': _user_brief(request, ed, {'stats': _editor_stats(ed, now - timedelta(days=30))}),
        'authors': authors,
        'log': [{'at': _iso(x['at']), 'what': x['what']} for x in log[:200]],
    })


# ── Books & money ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsMaster])
def books(request):
    """GET /api/master/books/?days=30 — contract pipeline and top books."""
    from apps.coins.models import ReadingHistory
    from apps.editorial.models import ContractApplication
    from apps.stories.models import Story

    days = _days(request)
    since = timezone.now() - timedelta(days=days)
    pipeline = dict(Story.objects.values_list('contract_status').annotate(n=Count('id')))
    pipeline['eligible_not_applied'] = Story.objects.filter(contract_eligible=True, contract_status='none').count()
    opens = _chapter_opens_by_slug(PageVisit.objects.filter(created_at__gte=since))
    readers = dict(ReadingHistory.objects.filter(read_at__gte=since).values('story')
                   .annotate(n=Count('user', distinct=True)).values_list('story', 'n'))
    top = sorted(Story.objects.filter(Q(slug__in=list(opens)) | Q(pk__in=list(readers))).select_related('author'),
                 key=lambda s: (opens.get(s.slug, 0), readers.get(s.pk, 0)), reverse=True)[:25]
    row = lambda s, extra=None: {  # noqa: E731
        'title': s.title, 'slug': s.slug, 'author': s.author.username, 'author_id': s.author_id,
        'status': s.status, 'contract_status': s.contract_status, 'chapters': s.total_chapters,
        'views': s.total_views, 'unlocks': s.total_unlocks, 'likes': s.total_likes,
        'rating': float(s.average_rating or 0), **(extra or {}),
    }
    recent_signed = ContractApplication.objects.filter(status='signed').select_related('story', 'author', 'assigned_se') \
        .order_by('-signed_at')[:20]
    return Response({
        'days': days,
        'pipeline': pipeline,
        'top_books': [row(s, {'period_reads': opens.get(s.slug, 0), 'period_readers': readers.get(s.pk, 0)})
                      for s in top],
        'all_time_top': [row(s) for s in Story.objects.select_related('author').order_by('-total_views')[:15]],
        'new_books': [row(s, {'created_at': _iso(s.created_at)})
                      for s in Story.objects.filter(created_at__gte=since).select_related('author').order_by('-created_at')[:25]],
        'recent_signed': [{'story': a.story.title, 'slug': a.story.slug, 'author': a.author.username,
                           'se': a.assigned_se.username if a.assigned_se else None, 'signed_at': _iso(a.signed_at)}
                          for a in recent_signed],
    })


@api_view(['GET'])
@permission_classes([IsMaster])
def revenue(request):
    """GET /api/master/revenue/?days=30 — purchases, gifts, VIP and author pay."""
    from apps.chapters.models import ChapterUnlockEarning
    from apps.coins.models import AuthorPayout, Purchase
    from apps.tips.models import Tip

    days = _days(request)
    now = timezone.now()
    since = now - timedelta(days=days)
    start_day = since.replace(hour=0, minute=0, second=0, microsecond=0)
    done = Purchase.objects.filter(status=Purchase.STATUS_COMPLETED, completed_at__gte=since)
    by_type = list(done.values('purchase_type').annotate(usd=Sum('amount_paid_usd'), n=Count('id')))
    daily = done.annotate(d=TruncDate('completed_at')).values('d').annotate(n=Sum('amount_paid_usd'))
    top_spenders = (Purchase.objects.filter(status=Purchase.STATUS_COMPLETED).values('user', 'user__username')
                    .annotate(usd=Sum('amount_paid_usd'), n=Count('id')).order_by('-usd')[:20])
    gifts = Tip.objects.filter(status=Tip.STATUS_COMPLETED, created_at__gte=since)
    earn = ChapterUnlockEarning.objects.aggregate(
        held=Sum('coins', filter=Q(status='held')),
        released_period=Sum('coins', filter=Q(status='released', released_at__gte=since)))
    return Response({
        'days': days,
        'total_usd': _usd(done.aggregate(t=Sum('amount_paid_usd'))['t']),
        'purchases': done.count(),
        'refunds': Purchase.objects.filter(status=Purchase.STATUS_REFUNDED, created_at__gte=since).count(),
        'by_type': [{'type': r['purchase_type'], 'usd': _usd(r['usd']), 'n': r['n']} for r in by_type],
        'daily': _series(daily, start_day, days),
        'top_spenders': [{'user_id': r['user'], 'username': r['user__username'], 'usd': _usd(r['usd']), 'n': r['n']}
                         for r in top_spenders],
        'gifts_usd': _usd(gifts.aggregate(t=Sum('amount_usd'))['t']),
        'coin_tips': gifts.filter(amount_usd__isnull=True).count(),
        'author_earnings_held_coins': earn['held'] or 0,
        'author_earnings_released_coins': earn['released_period'] or 0,
        'payouts': list(AuthorPayout.objects.values('status').annotate(usd=Sum('amount_usd'), n=Count('id'))),
        'vip_active': User.objects.filter(is_vip=True).filter(Q(vip_expires__isnull=True) | Q(vip_expires__gt=now)).count(),
    })


@api_view(['GET'])
@permission_classes([IsMaster])
def audience(request):
    """GET /api/master/audience/?days=30 — demographics, tech, acquisition,
    retention cohorts."""
    from apps.users.models import FCMDevice

    days = _days(request)
    now = timezone.now()
    since = now - timedelta(days=days)
    pv = PageVisit.objects.filter(created_at__gte=since)

    # Age (from date of birth)
    ages = Counter()
    today = timezone.localdate()
    for dob in User.objects.exclude(date_of_birth__isnull=True).values_list('date_of_birth', flat=True):
        a = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        ages['13–17' if a < 18 else '18–24' if a < 25 else '25–34' if a < 35 else '35–44' if a < 45 else '45+'] += 1
    genres = Counter()
    for g in User.objects.exclude(preferred_genres=[]).values_list('preferred_genres', flat=True)[:20000]:
        for x in (g or []):
            genres[str(x)] += 1

    # Most used screens / endpoints
    paths = Counter()
    for path, n in pv.values_list('path').annotate(n=Count('id')).order_by('-n')[:3000]:
        paths[_normalise(path)] += n
    referrers = list(pv.exclude(referrer='').exclude(referrer__icontains='novelux').exclude(referrer__icontains='huxnovel')
                     .values('referrer').annotate(n=Count('id')).order_by('-n')[:15])
    app_versions = list(FCMDevice.objects.filter(is_active=True).values('platform', 'app_version')
                        .annotate(n=Count('id')).order_by('-n')[:15])
    os_list = list(pv.exclude(os='').values('os').annotate(n=Count('ip_address', distinct=True)).order_by('-n')[:10])
    hours = [0] * 24
    for r in pv.annotate(h=ExtractHour('created_at')).values('h').annotate(n=Count('id')):
        hours[r['h']] = r['n']

    # Weekly retention: of people who joined in each week, how many came back
    cohorts = []
    for w in range(8, 0, -1):
        c_start = (now - timedelta(weeks=w)).replace(hour=0, minute=0, second=0, microsecond=0)
        c_end = c_start + timedelta(weeks=1)
        joined = dict(User.objects.filter(date_joined__gte=c_start, date_joined__lt=c_end)
                      .values_list('pk', 'date_joined'))
        if not joined:
            cohorts.append({'week': str(c_start.date()), 'size': 0, 'd1': 0, 'd7': 0, 'd30': 0})
            continue
        seen = defaultdict(set)
        for uid, t in (PageVisit.objects.filter(user_id__in=list(joined), created_at__gte=c_start)
                       .values_list('user_id', 'created_at').iterator()):
            seen[uid].add((t - joined[uid]).days)

        def kept(lo, hi):
            return sum(1 for uid in joined if any(lo <= d < hi for d in seen[uid]))
        size = len(joined)
        cohorts.append({'week': str(c_start.date()), 'size': size,
                        'd1': round(kept(1, 2) / size, 3), 'd7': round(kept(7, 14) / size, 3),
                        'd30': round(kept(30, 60) / size, 3)})

    return Response({
        'days': days,
        'ages': [{'name': k, 'value': v} for k, v in sorted(ages.items())],
        'genres': [{'name': k, 'value': v} for k, v in genres.most_common(12)],
        'languages': list(User.objects.values('preferred_language').annotate(n=Count('id')).order_by('-n')[:10]),
        'top_paths': [{'path': p, 'label': describe(p.replace('<slug>', 'x').replace('<n>', '1')), 'hits': n}
                      for p, n in paths.most_common(25)],
        'referrers': referrers,
        'app_versions': app_versions,
        'os': os_list,
        'hours': hours,
        'retention': cohorts,
    })


# ── Session replay ────────────────────────────────────────────────────────────
# There is no screen recording: the app's requests are turned back into the
# screens that made them. One screen usually fires several requests (a book
# page loads the book, its chapters, reviews…), so requests close together are
# merged and the most telling one names the screen.

_STORY_WORDS = {'mine', 'trending', 'featured', 'editors-pick', 'completed-stories', 'free-download',
                'world-famous', 'african-folktale', 'bookmarks', 'genres', 'subgenres', 'tags', 'banners',
                'library-banner', 'short-stories', 'new-arrivals', 'recommended', 'free-discount', 'rankings',
                'author-spotlight', 'explore-tab', 'ranking-section', 'genre-section', 'request',
                'my-promotions', 'reviews'}

# (regex, screen type, priority) — higher priority wins inside a merged group
_SCREENS = [
    (r'^/api/chapters/(?P<slug>[^/]+)/chapters/(?P<n>\d+)/unlock/?$', 'unlock', 12),
    (r'^/api/chapters/(?P<slug>[^/]+)/chapters/(?P<n>\d+)/ad-access/?$', 'ad_access', 12),
    (r'^/api/chapters/(?P<slug>[^/]+)/chapters/(?P<n>\d+)/?$', 'read', 10),
    (r'^/api/chapters/(?P<slug>[^/]+)/chapters/download/?$', 'download', 11),
    (r'^/api/chapters/(?P<slug>[^/]+)/chapters/?$', 'book', 6),
    (r'^/api/stories/(?P<slug>[^/]+)/(?:rate|like|bookmark|report)/?$', 'book', 7),
    (r'^/api/stories/(?P<slug>[^/]+)/?$', 'book', 8),
    (r'^/api/stories/(?:search|$)', 'search', 5),
    (r'^/api/stories/bookmarks', 'library', 6),
    (r'^/api/stories/', 'home', 3),
    (r'^/api/coins/(?:checkin|claim-reward|tasks|ad-tasks)', 'rewards', 7),
    (r'^/api/coins/(?:packages|plans|verify-purchases|checkout|vip-status)', 'store', 8),
    (r'^/api/coins/redeem', 'redeem', 8),
    (r'^/api/coins/history', 'library', 5),
    (r'^/api/coins/', 'wallet', 4),
    (r'^/api/tips/', 'gift', 9),
    (r'^/api/comments/', 'comments', 7),
    (r'^/api/stories/reviews/', 'comments', 7),
    (r'^/api/audio/', 'listen', 7),
    (r'^/api/notifications/', 'notifications', 5),
    (r'^/api/users/', 'profile', 5),
    (r'^/api/auth/(?:token|social|google|apple|dj/login)', 'login', 9),
    (r'^/api/auth/(?:dj/registration|register)', 'signup', 9),
    (r'^/api/auth/me', 'app_open', 1),
    (r'^/api/auth/', 'profile', 2),
    (r'^/api/editorial/', 'editor_dashboard', 6),
    (r'^/explore/(?P<slug>[^/]+)', 'book', 8),
    (r'^/story/(?P<slug>[^/]+)', 'book', 8),
    (r'^/author', 'author_dashboard', 6),
    (r'^/editorial', 'editor_dashboard', 6),
    (r'^/$', 'home', 3),
    (r'^/api/', 'app', 0),
    (r'^/', 'web', 0),
]
_SCREENS = [(re.compile(p), t, pr) for p, t, pr in _SCREENS]
MERGE_SECONDS = 4


def _screen_of(path):
    for rx, kind, prio in _SCREENS:
        m = rx.match(path or '')
        if m:
            gd = m.groupdict()
            slug = gd.get('slug')
            if slug and slug.lower() in _STORY_WORDS:
                return 'home', 3, {}
            return kind, prio, {k: v for k, v in gd.items() if v}
    return 'app', 0, {}


def _build_screens(visits):
    """Visits (oldest first) → screens: [{at, until, type, slug, n, paths, …}]"""
    screens = []
    for v in visits:
        kind, prio, params = _screen_of(v.path)
        cur = screens[-1] if screens else None
        same_place = cur and (not params.get('slug') or not cur.get('slug') or params.get('slug') == cur.get('slug'))
        if cur and (v.created_at - cur['_last']).total_seconds() <= MERGE_SECONDS and same_place \
                and not (kind in ('read', 'unlock', 'ad_access') and cur['type'] in ('read', 'unlock', 'ad_access')
                         and params.get('n') != cur.get('n')):
            cur['_last'] = v.created_at
            cur['paths'].append(v.path)
            if prio > cur['_prio']:
                cur.update(type=kind, _prio=prio, **params)
            continue
        screens.append({'at': v.created_at, '_last': v.created_at, '_prio': prio, 'type': kind,
                        'paths': [v.path], 'platform': _platform(v.os, v.device_type),
                        'city': v.city, 'country': v.country, 'country_code': v.country_code, **params})
    for i, s in enumerate(screens):
        s['until'] = screens[i + 1]['at'] if i + 1 < len(screens) else s['_last']
    return screens


@api_view(['GET'])
@permission_classes([IsMaster])
def replay(request, user_id):
    """GET /api/master/users/<id>/replay/?start=<iso>   one session
           /api/master/users/<id>/replay/?live=1        the last 20 minutes
    Rebuilds the screens a person went through, with the real books and
    chapters, for the dashboard's phone replay."""
    from django.utils.dateparse import parse_datetime
    from apps.chapters.models import Chapter, strip_html
    from apps.coins.models import CheckinStreak
    from apps.stories.models import Story

    u = get_object_or_404(User, pk=user_id)
    now = timezone.now()
    visits_qs = PageVisit.objects.filter(user=u)

    # Sessions over the last 30 days (newest first) for the picker
    times = list(visits_qs.filter(created_at__gte=now - timedelta(days=30))
                 .order_by('-created_at').values_list('created_at', flat=True)[:20000])
    sessions = sorted(_sessions(times), key=lambda x: x[0], reverse=True)[:60]

    live = request.query_params.get('live') in ('1', 'true')
    if live:
        win_start, win_end = now - timedelta(minutes=20), now
    else:
        raw = (request.query_params.get('start') or '').replace(' ', '+')  # unencoded "+00:00"
        start = parse_datetime(raw) if raw else None
        chosen = next((s for s in sessions if start and abs((s[0] - start).total_seconds()) < 1), None) \
            or (sessions[0] if sessions else None)
        win_start, win_end = (chosen[0], chosen[1]) if chosen else (now, now)
    visits = list(visits_qs.filter(created_at__gte=win_start, created_at__lte=win_end + timedelta(seconds=1))
                  .order_by('created_at')[:3000])
    screens = _build_screens(visits)[-400:]

    # Fill screens with the real books and chapters
    slugs = {s['slug'] for s in screens if s.get('slug')}
    stories = {st.slug: st for st in Story.objects.filter(slug__in=slugs).select_related('author', 'genre')}
    want = {(s['slug'], int(s['n'])) for s in screens if s.get('slug') and s.get('n')}
    chapters = {}
    if want:
        for ch in Chapter.objects.filter(story__slug__in={w[0] for w in want},
                                         chapter_number__in={w[1] for w in want}).select_related('story'):
            chapters[(ch.story.slug, ch.chapter_number)] = ch

    def story_card(st):
        if not st:
            return None
        cover = None
        try:
            cover = request.build_absolute_uri(st.cover_image.url) if st.cover_image else None
        except Exception:
            pass
        return {'title': st.title, 'slug': st.slug, 'cover': cover, 'author': st.author.username,
                'genre': st.genre.name if st.genre_id else '', 'chapters': st.total_chapters,
                'views': st.total_views, 'rating': float(st.average_rating or 0),
                'synopsis': (st.description or st.synopsis or '')[:400]}

    labels = {'home': 'Home', 'search': 'Search', 'book': 'Book page', 'read': 'Reading', 'unlock': 'Unlocked',
              'ad_access': 'Watched an ad to read', 'download': 'Downloading the book', 'library': 'Library',
              'rewards': 'Rewards & check-in', 'store': 'Coin store / VIP', 'redeem': 'Redeem coins', 'wallet': 'Wallet',
              'gift': 'Sent a gift', 'comments': 'Comments', 'listen': 'Listening', 'notifications': 'Notifications',
              'profile': 'Profile', 'login': 'Signing in', 'signup': 'Signing up', 'app_open': 'Opened the app',
              'author_dashboard': 'Author dashboard (web)', 'editor_dashboard': 'Editor dashboard (web)'}
    out = []
    last_slug = None
    for s in screens:
        # Gifts and comments don't name the book — it's the one they were on
        if s['type'] in ('gift', 'comments') and not s.get('slug') and last_slug:
            s['slug'] = last_slug
        if s.get('slug'):
            last_slug = s['slug']
        label = labels.get(s['type'])
        if label and s.get('n'):
            label += f" · Chapter {s['n']}"
        item = {'at': _iso(s['at']), 'until': _iso(s['until']), 'type': s['type'],
                'doing': label or describe(next((p for p in s['paths'] if _screen_of(p)[0] == s['type']), s['paths'][0])),
                'requests': len(s['paths']), 'platform': s['platform'],
                'place': ', '.join(x for x in (s['city'], s['country']) if x), 'country_code': s['country_code']}
        st = stories.get(s.get('slug'))
        if s.get('slug'):
            item['story'] = story_card(st) or {'title': s['slug'].replace('-', ' ').title(), 'slug': s['slug']}
        if s.get('n'):
            ch = chapters.get((s.get('slug'), int(s['n'])))
            item['chapter'] = {'number': int(s['n']), 'title': ch.title if ch else f'Chapter {s["n"]}',
                               'locked': bool(ch and ch.is_locked), 'coin_cost': ch.coin_cost if ch else 0,
                               'excerpt': strip_html(re.sub(r'(?i)</p>|<br\s*/?>', '\n\n', ch.content or ''))[:900].strip()
                               if ch else ''}
        out.append(item)

    # Covers for a believable home screen
    popular = [story_card(x) for x in Story.objects.select_related('author', 'genre').order_by('-total_views')[:6]]
    streak = CheckinStreak.objects.filter(user=u).values('current_streak', 'longest_streak').first()
    return Response({
        'user': _user_brief(request, u, {'coins': u.coin_balance, 'bonus': u.bonus_balance, 'streak': streak}),
        'live': live,
        'window': {'start': _iso(win_start), 'end': _iso(win_end)},
        'sessions': [{'start': _iso(a), 'end': _iso(b), 'hits': n,
                      'minutes': round((b - a).total_seconds() / 60, 1)} for a, b, n in sessions],
        'screens': out,
        'home_books': popular,
    })
