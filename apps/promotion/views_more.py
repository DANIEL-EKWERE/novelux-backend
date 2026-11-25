"""/api/promotion/… part 2 — author promotion tasks, and analytics:
book growth, movers and candidates, and how promotions performed."""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Max, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.editorial.permissions import IsPromo
from .models import Placement, PromotionLog, PromotionTask
from .views import _book, _iso


def _notify(user, title, message, data=None, push=True):
    try:
        from apps.notifications.services import create_notification
        create_notification(user, 'system', title, message, data=data or {}, send_push=push)
    except Exception:
        pass


def _task(request, t, now=None, with_progress=True):
    return {'id': t.id, 'book': _book(request, t.story), 'author': t.author.username, 'title': t.title,
            'message': t.message, 'chapters_per_day': t.chapters_per_day, 'duration_days': t.duration_days,
            'reward': t.reward, 'promotion_start': t.promotion_start.isoformat() if t.promotion_start else None,
            'respond_by': _iso(t.respond_by), 'conditions': t.conditions, 'status': t.status,
            'status_label': t.get_status_display(), 'accepted_at': _iso(t.accepted_at),
            'responded_at': _iso(t.responded_at), 'decline_reason': t.decline_reason,
            'created_at': _iso(t.created_at), 'by': t.created_by.username if t.created_by_id else '',
            'progress': t.progress(now) if with_progress else None}


# ── Promotion tasks (team side) ───────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsPromo])
def tasks(request):
    from apps.stories.models import Story
    if request.method == 'GET':
        qs = PromotionTask.objects.select_related('story__author', 'story__genre', 'author', 'created_by')
        st = request.query_params.get('status')
        if st and st != 'all':
            qs = qs.filter(status=st)
        rows = list(qs[:200])
        now = timezone.now()
        for t in rows:
            t.refresh_status(now)
        return Response({'results': [_task(request, t, now) for t in rows]})
    d = request.data
    story = get_object_or_404(Story.objects.select_related('author'), pk=d.get('story_id'))
    for f in ('title', 'message', 'reward'):
        if not (d.get(f) or '').strip():
            return Response({'detail': f'Fill in the {f}.'}, status=400)
    try:
        cpd = max(1, min(int(d.get('chapters_per_day') or 1), 20))
        days = max(1, min(int(d.get('duration_days') or 7), 90))
    except (TypeError, ValueError):
        return Response({'detail': 'Chapters per day and duration must be numbers.'}, status=400)
    resp = parse_datetime(str(d.get('respond_by') or '')) if d.get('respond_by') else None
    if resp and timezone.is_naive(resp):
        resp = timezone.make_aware(resp)
    t = PromotionTask.objects.create(
        story=story, author=story.author, title=d['title'].strip()[:150], message=d['message'].strip(),
        chapters_per_day=cpd, duration_days=days, reward=d['reward'].strip()[:255],
        promotion_start=parse_date(str(d.get('promotion_start') or '')) if d.get('promotion_start') else None,
        respond_by=resp, conditions=(d.get('conditions') or '').strip(), created_by=request.user)
    _notify(story.author, f'🎉 Promotion offer: {t.title}',
            f'{t.message[:200]} Open your author dashboard → Promotions to accept.',
            {'screen': 'my_books', 'slug': story.slug, 'promotion_task': t.id})
    PromotionLog.objects.create(user=request.user, action='task_sent', story=story,
                                note=f'{t.title}: {cpd}/day for {days} days → {t.reward}'[:255])
    return Response({'detail': f'Offer sent to {story.author.username}.', 'task': _task(request, t)}, status=201)


@api_view(['PATCH'])
@permission_classes([IsPromo])
def task_detail(request, pk):
    """PATCH {status: qualified|cancelled|met|missed} or edit the offer while it's waiting;
    {remind: true} re-sends the notification."""
    t = get_object_or_404(PromotionTask.objects.select_related('story', 'author'), pk=pk)
    d = request.data
    if d.get('remind'):
        _notify(t.author, f'⏳ Reminder: {t.title}',
                f'{t.chapters_per_day} chapter(s) a day keeps "{t.story.title}" on track for {t.reward}.',
                {'screen': 'my_books', 'slug': t.story.slug, 'promotion_task': t.id})
        return Response({'detail': 'Reminder sent.'})
    if t.status == 'sent':
        for f in ('title', 'message', 'reward', 'conditions'):
            if f in d:
                setattr(t, f, str(d[f]).strip())
    new = d.get('status')
    if new in ('qualified', 'cancelled', 'met', 'missed'):
        t.status = new
        if new == 'qualified':
            _notify(t.author, f'🏆 "{t.story.title}" qualified!',
                    f'You met the requirements — {t.reward}'
                    + (f' starts {t.promotion_start:%d %b}.' if t.promotion_start else '.'),
                    {'screen': 'my_books', 'slug': t.story.slug})
        elif new == 'cancelled':
            _notify(t.author, f'Promotion offer withdrawn: {t.title}', 'This promotion offer is no longer available.',
                    {'screen': 'my_books', 'slug': t.story.slug}, push=False)
    t.save()
    PromotionLog.objects.create(user=request.user, action='task_updated', story=t.story, note=f'{t.title}: {t.status}'[:255])
    return Response({'detail': 'Updated.', 'task': _task(request, t)})


# ── Promotion tasks (author side) ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_tasks(request):
    rows = list(PromotionTask.objects.filter(author=request.user).exclude(status='cancelled')
                .select_related('story__author', 'story__genre', 'author', 'created_by')[:50])
    now = timezone.now()
    for t in rows:
        t.refresh_status(now)
    return Response({'results': [_task(request, t, now) for t in rows if t.status != 'cancelled']})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def my_task_respond(request, pk):
    """POST {accept: true|false, reason}"""
    t = get_object_or_404(PromotionTask.objects.select_related('story', 'created_by'), pk=pk, author=request.user)
    t.refresh_status()
    if t.status != 'sent':
        return Response({'detail': 'This offer is no longer open.'}, status=400)
    accept = str(request.data.get('accept', '')).lower() in ('1', 'true', 'yes')
    now = timezone.now()
    t.status, t.responded_at = ('accepted' if accept else 'declined'), now
    if accept:
        t.accepted_at = now
    else:
        t.decline_reason = (request.data.get('reason') or '').strip()[:255]
    t.save()
    if t.created_by:
        _notify(t.created_by, f'{request.user.username} {"accepted" if accept else "declined"} "{t.title}"',
                f'Book: {t.story.title}.' + (f' Reason: {t.decline_reason}' if t.decline_reason else ''), push=False)
    return Response({'detail': ('Accepted — the clock starts now. Upload %d chapter(s) a day.' % t.chapters_per_day)
                     if accept else 'Declined.', 'task': _task(request, t)})


# ── Analytics ─────────────────────────────────────────────────────────────────

def _views(story_ids, start, end):
    """{story_id: (views, unlocks)} between two dates (inclusive)."""
    from apps.stories.models import StoryDailyStats
    out = {}
    for sid, v, u in (StoryDailyStats.objects.filter(story_id__in=story_ids, date__gte=start, date__lte=end)
                      .values('story_id').annotate(v=Sum('views'), u=Sum('unlocks')).values_list('story_id', 'v', 'u')):
        out[sid] = (v or 0, u or 0)
    return out


def _pct(now, before):
    if not before:
        return None if not now else 100.0
    return round((now - before) * 100 / before, 1)


@api_view(['GET'])
@permission_classes([IsPromo])
def movers(request):
    """GET …/analytics/movers/?days=7&genre=&status=&promoted=yes|no
    Rising, declining, organic candidates, stalled updates, searched-but-unread."""
    from apps.chapters.models import Chapter
    from apps.stories.models import Story
    from .models import SearchLog
    days = max(1, min(int(request.query_params.get('days', 7)), 90))
    today = timezone.localdate()
    cur_a, prev_a = today - timedelta(days=days - 1), today - timedelta(days=2 * days - 1)
    books = Story.objects.exclude(status__in=['draft', 'rejected']).exclude(author__is_banned=True).select_related('author', 'genre')
    if request.query_params.get('genre'):
        books = books.filter(genre_id=request.query_params['genre'])
    if request.query_params.get('status') in ('ongoing', 'completed', 'paused'):
        books = books.filter(status=request.query_params['status'])
    now = timezone.now()
    live_ids = set(Placement.objects.filter(cancelled=False, starts_at__lte=now)
                   .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).values_list('story_id', flat=True))
    if request.query_params.get('promoted') == 'yes':
        books = books.filter(pk__in=live_ids)
    elif request.query_params.get('promoted') == 'no':
        books = books.exclude(pk__in=live_ids)
    books = {s.pk: s for s in books}
    cur = _views(books, cur_a, today)
    prev = _views(books, prev_a, cur_a - timedelta(days=1))
    last_ch = dict(Chapter.objects.filter(story_id__in=books).exclude(status__in=['draft', 'rejected'])
                   .values('story_id').annotate(m=Max('created_at')).values_list('story_id', 'm'))
    rows = []
    for sid, s in books.items():
        v, u = cur.get(sid, (0, 0))
        pv = prev.get(sid, (0, 0))[0]
        last = last_ch.get(sid)
        rows.append({**_book(request, s), 'period_views': v, 'prev_views': pv, 'unlocks': u, 'growth': _pct(v, pv),
                     'promoted_now': sid in live_ids,
                     'days_since_update': (now - last).days if last else None})
    floor = 20 * days / 7                      # ignore tiny numbers
    rising = sorted([r for r in rows if r['period_views'] >= floor and (r['growth'] or 0) > 0],
                    key=lambda r: -(r['growth'] or 0))[:15]
    declining = sorted([r for r in rows if r['prev_views'] >= floor and (r['growth'] or 0) < 0],
                       key=lambda r: r['growth'])[:15]
    candidates = sorted([r for r in rows if not r['promoted_now'] and r['period_views'] >= floor
                         and (r['growth'] or 0) >= 10 and (r['days_since_update'] is not None and r['days_since_update'] <= 14)],
                        key=lambda r: -(r['period_views'] * (1 + (r['growth'] or 0) / 100) + r['rating'] * 50))[:15]
    stalled = sorted([r for r in rows if r['period_views'] >= floor and r['status'] != 'completed'
                      and (r['days_since_update'] is None or r['days_since_update'] > 14)],
                     key=lambda r: -r['period_views'])[:15]
    # Searched for but little read
    from django.db.models import Count
    searches = list(SearchLog.objects.filter(created_at__gte=now - timedelta(days=days)).values('query')
                    .annotate(n=Count('id')).order_by('-n')[:40])
    searched = []
    for q in searches:
        hit = next((r for r in rows if q['query'] in r['title'].lower()), None)
        if hit and hit['period_views'] < max(q['n'] * 2, floor):
            searched.append({**hit, 'searches': q['n'], 'query': q['query']})
    return Response({'days': days, 'rising': rising, 'declining': declining, 'candidates': candidates,
                     'stalled': stalled, 'searched_low_reads': searched[:15],
                     'top_searches': [{'query': q['query'], 'count': q['n']} for q in searches[:15]]})


@api_view(['GET'])
@permission_classes([IsPromo])
def book_trend(request, pk):
    """GET …/analytics/books/<id>/?days=90 — daily views and unlocks, chapters
    uploaded, and each promotion with before / during / after."""
    from apps.chapters.models import Chapter
    from apps.stories.models import Story, StoryDailyStats
    s = get_object_or_404(Story.objects.select_related('author', 'genre'), pk=pk)
    days = max(7, min(int(request.query_params.get('days', 90)), 365))
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    stats = {d.date: d for d in StoryDailyStats.objects.filter(story=s, date__gte=start)}
    ch = defaultdict(int)
    for t in Chapter.objects.filter(story=s, created_at__date__gte=start).exclude(status__in=['draft', 'rejected']) \
            .values_list('created_at', flat=True):
        ch[timezone.localtime(t).date()] += 1
    series = []
    for i in range(days):
        d = start + timedelta(days=i)
        st = stats.get(d)
        series.append({'date': d.isoformat(), 'views': st.views if st else 0, 'unlocks': st.unlocks if st else 0,
                       'chapters': ch.get(d, 0)})

    def total(a, b):
        return sum(x['views'] for x in series if a <= x['date'] <= b)
    t = today.isoformat()
    week, month = (today - timedelta(days=6)).isoformat(), (today - timedelta(days=29)).isoformat()
    prev_week = ((today - timedelta(days=13)).isoformat(), (today - timedelta(days=7)).isoformat())
    return Response({'book': _book(request, s, full=True), 'series': series,
                     'totals': {'today': total(t, t), 'week': total(week, t), 'month': total(month, t),
                                'week_growth': _pct(total(week, t), total(*prev_week))},
                     'promotions': [_lift(request, p) for p in Placement.objects.filter(story=s, cancelled=False)
                                    .select_related('shelf', 'story__author', 'story__genre', 'created_by').order_by('-starts_at')[:20]]})


def _lift(request, p):
    """Views/unlocks before, during and after a placement (same length each)."""
    from .views import _placement
    today = timezone.localdate()
    a = timezone.localtime(p.starts_at).date()
    b = min(timezone.localtime(p.ends_at).date() if p.ends_at else today, today)
    if a > today:
        return {**_placement(request, p), 'before': None, 'during': None, 'after': None, 'lift': None}
    span = (b - a).days + 1
    before = _views([p.story_id], a - timedelta(days=span), a - timedelta(days=1)).get(p.story_id, (0, 0))
    during = _views([p.story_id], a, b).get(p.story_id, (0, 0))
    after = None
    if p.ends_at and b < today:
        after = _views([p.story_id], b + timedelta(days=1), min(b + timedelta(days=span), today)).get(p.story_id, (0, 0))
    return {**_placement(request, p), 'days': span,
            'before': {'views': before[0], 'unlocks': before[1]}, 'during': {'views': during[0], 'unlocks': during[1]},
            'after': {'views': after[0], 'unlocks': after[1]} if after else None, 'lift': _pct(during[0], before[0])}


@api_view(['GET'])
@permission_classes([IsPromo])
def promotion_results(request):
    """GET …/analytics/promotions/?days=60 — every placement's lift, each
    shelf's average, plus pop-ups (shown/tapped) and social posts."""
    now = timezone.now()
    days = max(7, min(int(request.query_params.get('days', 60)), 365))
    qs = (Placement.objects.filter(cancelled=False, starts_at__gte=now - timedelta(days=days), starts_at__lte=now)
          .select_related('shelf', 'story__author', 'story__genre', 'created_by').order_by('-starts_at')[:300])
    rows = [_lift(request, p) for p in qs]
    shelves = defaultdict(list)
    for r in rows:
        if r['lift'] is not None:
            shelves[r['shelf']].append(r)
    by_shelf = sorted([{'shelf': k, 'placements': len(v), 'avg_lift': round(sum(x['lift'] for x in v) / len(v), 1),
                        'views_during': sum(x['during']['views'] for x in v)} for k, v in shelves.items()],
                      key=lambda x: -x['avg_lift'])
    from apps.promos.models import InAppPromo
    pops = [{'book': p.story.title, 'kind': p.get_kind_display(), 'shown': p.impressions, 'tapped': p.clicks,
             'ctr': round(p.clicks * 100 / p.impressions, 1) if p.impressions else None, 'starts_at': _iso(p.starts_at)}
            for p in InAppPromo.objects.filter(starts_at__gte=now - timedelta(days=days)).select_related('story')[:50]]
    social = []
    try:
        from apps.social.models import SocialPostTarget
        for t in (SocialPostTarget.objects.filter(status='published', published_at__gte=now - timedelta(days=days))
                  .select_related('post__story', 'account').order_by('-published_at')[:60]):
            m = t.metrics or {}
            social.append({'text': t.post.text[:90], 'book': t.post.story.title if t.post.story_id else '',
                           'network': t.account.get_platform_display(), 'url': t.url,
                           'views': m.get('views') or m.get('impressions') or 0, 'likes': m.get('likes', 0),
                           'comments': m.get('comments', 0), 'shares': m.get('shares', 0), 'at': _iso(t.published_at)})
    except Exception:
        pass
    return Response({'days': days, 'placements': rows, 'by_shelf': by_shelf, 'popups': pops, 'social': social,
                     'note': 'Lift compares a book\'s views while promoted with the same number of days before. '
                             'Exact shelf impressions and taps need the next app update.'})
