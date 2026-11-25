"""/api/promotion/… — the Promotion team's dashboard API: browse books, run
shelves (slots, scheduled sets, daily rotations), see the calendar and
clashes, handle SE promotion requests, and keep a history."""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.editorial.permissions import IsPromo
from .models import Placement, Shelf


def _when(value):
    if not value:
        return None
    dt = parse_datetime(str(value))
    if dt and timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def _iso(dt):
    return dt.isoformat() if dt else None


def _cover(request, story):
    try:
        return request.build_absolute_uri(story.cover_image.url) if story.cover_image else None
    except Exception:
        return None


def _book(request, s, full=False):
    d = {'id': s.pk, 'slug': s.slug, 'title': s.title, 'author': s.author.username if s.author_id else '',
         'cover': _cover(request, s), 'genre': s.genre.name if s.genre_id else '', 'status': s.status,
         'views': s.total_views, 'rating': float(s.average_rating or 0), 'chapters': s.total_chapters}
    if full:
        d.update(description=(s.description or '')[:1500], synopsis=getattr(s, 'synopsis', '') or '',
                 contract_status=s.contract_status, likes=s.total_likes, comments=s.total_comments,
                 words=s.word_count, created_at=_iso(s.created_at), updated_at=_iso(s.updated_at))
    return d


def _placement(request, p, now=None):
    return {'id': p.id, 'shelf_id': p.shelf_id, 'shelf': p.shelf.name, 'shelf_group': p.shelf.group,
            'book': _book(request, p.story), 'position': p.position, 'starts_at': _iso(p.starts_at),
            'ends_at': _iso(p.ends_at), 'status': p.status(now), 'label': p.label, 'note': p.note,
            'source': p.get_source_display(), 'request_id': p.request_id,
            'by': p.created_by.username if p.created_by_id else ''}


def _log(user, action, **detail):
    from .models import PromotionLog
    PromotionLog.objects.create(user=user, action=action, **detail)


# ── Books ─────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsPromo])
def books(request):
    """GET …/books/?q=&genre=&status=&promoted=yes|no&sort=views|new|rating|updated&page="""
    from apps.stories.models import Story
    qs = Story.objects.exclude(status__in=['draft', 'rejected']).exclude(author__is_banned=True) \
        .select_related('author', 'genre')
    q = (request.query_params.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(author__username__icontains=q) | Q(description__icontains=q))
    if request.query_params.get('genre'):
        qs = qs.filter(genre_id=request.query_params['genre'])
    if request.query_params.get('status') in ('ongoing', 'completed', 'paused'):
        qs = qs.filter(status=request.query_params['status'])
    now = timezone.now()
    live = Placement.objects.filter(cancelled=False, starts_at__lte=now).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
    if request.query_params.get('promoted') == 'yes':
        qs = qs.filter(pk__in=live.values('story_id'))
    elif request.query_params.get('promoted') == 'no':
        qs = qs.exclude(pk__in=live.values('story_id'))
    sort = {'new': '-created_at', 'rating': '-average_rating', 'updated': '-updated_at'}.get(
        request.query_params.get('sort'), '-total_views')
    qs = qs.order_by(sort)
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except ValueError:
        page = 1
    total = qs.count()
    rows = list(qs[(page - 1) * 24: page * 24])
    on = defaultdict(list)
    for sid, name in live.filter(story_id__in=[s.pk for s in rows]).values_list('story_id', 'shelf__name'):
        on[sid].append(name)
    return Response({'total': total, 'page': page, 'pages': (total + 23) // 24,
                     'results': [{**_book(request, s), 'on_shelves': on.get(s.pk, [])} for s in rows]})


@api_view(['GET'])
@permission_classes([IsPromo])
def book_detail(request, pk):
    from apps.stories.models import Story
    s = get_object_or_404(Story.objects.select_related('author', 'genre'), pk=pk)
    history = [_placement(request, p) for p in Placement.objects.filter(story=s).select_related('shelf', 'story__author', 'story__genre', 'created_by').order_by('-starts_at')[:20]]
    return Response({'book': _book(request, s, full=True), 'placements': history})


@api_view(['GET'])
@permission_classes([IsPromo])
def genres(request):
    from apps.stories.models import Genre
    return Response([{'id': g.pk, 'name': g.name} for g in Genre.objects.filter(is_active=True).order_by('name')])


# ── Shelves ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsPromo])
def shelves(request):
    """All shelves with their slots, what's live now and what's coming up."""
    Shelf.ensure_defaults()
    now = timezone.now()
    out = []
    counts_live = defaultdict(int)
    counts_next = defaultdict(int)
    for sid, st, en, paused in (Placement.objects.filter(cancelled=False).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
                                .values_list('shelf_id', 'starts_at', 'ends_at', 'paused')):
        if st <= now and not paused:
            counts_live[sid] += 1
        elif st > now:
            counts_next[sid] += 1
    for s in Shelf.objects.all():
        out.append({'id': s.pk, 'key': s.key, 'name': s.name, 'group': s.group, 'capacity': s.capacity,
                    'is_active': s.is_active, 'live': min(counts_live[s.pk], s.capacity), 'upcoming': counts_next[s.pk]})
    return Response(out)


@api_view(['GET', 'PATCH'])
@permission_classes([IsPromo])
def shelf_detail(request, pk):
    """GET: the shelf's slots at a moment (?at=) + every set scheduled.
    PATCH {capacity, is_active}"""
    shelf = get_object_or_404(Shelf, pk=pk)
    if request.method == 'PATCH':
        if 'capacity' in request.data:
            shelf.capacity = max(1, min(int(request.data['capacity']), 50))
        if 'is_active' in request.data:
            shelf.is_active = str(request.data['is_active']).lower() in ('1', 'true')
        shelf.save()
        _log(request.user, 'shelf_updated', shelf=shelf, note=f'{shelf.capacity} slots, {"on" if shelf.is_active else "off"}')
    at = _when(request.query_params.get('at')) or timezone.now()
    qs = Placement.objects.filter(shelf=shelf, cancelled=False).select_related('story__author', 'story__genre', 'shelf', 'created_by')
    live = [p for p in qs.filter(starts_at__lte=at).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=at)).order_by('position', '-starts_at')]
    slots = []
    for n in range(1, shelf.capacity + 1):
        here = [p for p in live if p.position == n and not p.paused]
        slots.append({'position': n, 'placement': _placement(request, here[0], at) if here else None,
                      'clash': len(here) > 1})
    extra = [p for p in live if p.position > shelf.capacity]
    upcoming = qs.filter(Q(ends_at__isnull=True) | Q(ends_at__gt=timezone.now())).order_by('starts_at', 'position')
    return Response({'shelf': {'id': shelf.pk, 'name': shelf.name, 'group': shelf.group, 'key': shelf.key,
                               'capacity': shelf.capacity, 'is_active': shelf.is_active},
                     'at': _iso(at), 'slots': slots, 'over_capacity': [_placement(request, p, at) for p in extra],
                     'schedule': [_placement(request, p) for p in upcoming[:300]]})


# ── Placing books ─────────────────────────────────────────────────────────────

def _conflicts(shelf, story_id, position, starts, ends, exclude=None):
    """Clashes for a new placement: the slot already taken, or the same book
    already on this shelf, at an overlapping time."""
    qs = Placement.objects.filter(shelf=shelf, cancelled=False)
    if exclude:
        qs = qs.exclude(pk=exclude)
    overlap = qs.filter(Q(ends_at__isnull=True) | Q(ends_at__gt=starts))
    if ends:
        overlap = overlap.filter(starts_at__lt=ends)
    out = []
    for p in overlap.select_related('story'):
        if p.position == position:
            out.append(f'Slot {position} already has "{p.story.title}" from {p.starts_at:%d %b %H:%M}.')
        elif p.story_id == story_id:
            out.append(f'"{p.story.title}" is already on this shelf (slot {p.position}) at that time.')
    return out


@api_view(['POST'])
@permission_classes([IsPromo])
def schedule(request):
    """POST …/schedule/ — place a set of books on a shelf.
    { shelf_id, starts_at, ends_at | hours | days, label, note,
      books: [story_id, …]  (slot 1, 2, 3… in this order)
      or placements: [{story_id, position}, …],
      replace: true  → end whatever is in those slots when this set starts }"""
    from apps.stories.models import Story
    shelf = get_object_or_404(Shelf, pk=request.data.get('shelf_id'))
    starts = _when(request.data.get('starts_at')) or timezone.now()
    ends = _when(request.data.get('ends_at'))
    if not ends and request.data.get('days'):
        ends = starts + timedelta(days=float(request.data['days']))
    if not ends and request.data.get('hours'):
        ends = starts + timedelta(hours=float(request.data['hours']))
    if ends and ends <= starts:
        return Response({'detail': 'The end must be after the start.'}, status=400)
    items = request.data.get('placements') or [{'story_id': sid, 'position': i + 1}
                                               for i, sid in enumerate(request.data.get('books') or [])]
    if not items:
        return Response({'detail': 'Choose at least one book.'}, status=400)
    if len(items) > shelf.capacity:
        return Response({'detail': f'{shelf.name} has {shelf.capacity} slots — you picked {len(items)} books.'}, status=400)
    stories = {s.pk: s for s in Story.objects.filter(pk__in=[int(i['story_id']) for i in items])}
    replace = str(request.data.get('replace', 'true')).lower() in ('1', 'true')
    warnings = []
    created = []
    for it in items:
        sid, pos = int(it['story_id']), int(it.get('position') or 1)
        if sid not in stories:
            return Response({'detail': 'One of the books was not found.'}, status=400)
        if replace:
            # The new set takes over its slots when it starts
            for p in Placement.objects.filter(shelf=shelf, position=pos, cancelled=False, starts_at__lt=starts) \
                    .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=starts)):
                p.ends_at = starts
                p.save(update_fields=['ends_at'])
        warnings += _conflicts(shelf, sid, pos, starts, ends)
        created.append(Placement(shelf=shelf, story=stories[sid], position=pos, starts_at=starts, ends_at=ends,
                                 label=(request.data.get('label') or '')[:80], note=(request.data.get('note') or '')[:255],
                                 created_by=request.user, source=Placement.SOURCE_TEAM))
    Placement.objects.bulk_create(created)
    _log(request.user, 'scheduled', shelf=shelf, note=f'{len(created)} book(s) from {starts:%d %b %H:%M}'
         + (f' to {ends:%d %b %H:%M}' if ends else ''))
    return Response({'detail': f'{len(created)} book(s) scheduled on {shelf.name}.', 'warnings': warnings}, status=201)


@api_view(['POST'])
@permission_classes([IsPromo])
def rotation(request):
    """POST …/rotation/ — a daily rotation prepared in advance.
    { shelf_id, start_date (YYYY-MM-DD), switch_time ("08:00"), tz_offset_minutes,
      days: [[story_id…], [story_id…], …]   (one list per day, slot order) }"""
    from datetime import date, datetime, time, timezone as dt_tz
    from apps.stories.models import Story
    shelf = get_object_or_404(Shelf, pk=request.data.get('shelf_id'))
    days = request.data.get('days') or []
    if not days or not any(days):
        return Response({'detail': 'Add books for at least one day.'}, status=400)
    try:
        d0 = date.fromisoformat(request.data.get('start_date'))
        hh, mm = [int(x) for x in (request.data.get('switch_time') or '08:00').split(':')]
        offset = timedelta(minutes=int(request.data.get('tz_offset_minutes') or 0))
    except (TypeError, ValueError):
        return Response({'detail': 'Choose a start date and switch time.'}, status=400)
    for i, day in enumerate(days):
        if len(day) > shelf.capacity:
            return Response({'detail': f'Day {i + 1} has {len(day)} books — {shelf.name} has {shelf.capacity} slots.'}, status=400)
    ids = {int(x) for day in days for x in day}
    stories = {s.pk: s for s in Story.objects.filter(pk__in=ids)}
    created = []
    for i, day in enumerate(days):
        # The browser sends its UTC offset so "08:00" means 8am for the planner
        start = timezone.make_aware(datetime.combine(d0 + timedelta(days=i), time(hh, mm)), dt_tz.utc) - offset
        end = start + timedelta(days=1)
        for pos, sid in enumerate(day, 1):
            if int(sid) in stories:
                created.append(Placement(shelf=shelf, story=stories[int(sid)], position=pos, starts_at=start,
                                         ends_at=end, label=f'Day {i + 1} — {(d0 + timedelta(days=i)):%a %d %b}',
                                         created_by=request.user, source=Placement.SOURCE_TEAM))
    Placement.objects.bulk_create(created)
    _log(request.user, 'rotation', shelf=shelf, note=f'{len(days)} day(s), {len(created)} placement(s) from {d0:%d %b}')
    return Response({'detail': f'Rotation ready: {len(days)} day(s), switching daily at {hh:02d}:{mm:02d}.',
                     'placements': len(created)}, status=201)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsPromo])
def placement_detail(request, pk):
    """PATCH {starts_at, ends_at, position, paused, end_now, extend_days} · DELETE = cancel"""
    p = get_object_or_404(Placement.objects.select_related('shelf', 'story'), pk=pk)
    now = timezone.now()
    if request.method == 'DELETE':
        p.cancelled = True
        p.save(update_fields=['cancelled'])
        _log(request.user, 'cancelled', shelf=p.shelf, story=p.story)
        return Response({'detail': 'Cancelled.'})
    d = request.data
    if str(d.get('end_now', '')).lower() in ('1', 'true'):
        p.ends_at = now
    if d.get('extend_days'):
        p.ends_at = max(p.ends_at or now, now) + timedelta(days=float(d['extend_days']))
    if 'starts_at' in d and d['starts_at']:
        p.starts_at = _when(d['starts_at'])
    if 'ends_at' in d:
        p.ends_at = _when(d['ends_at'])
    if 'position' in d:
        p.position = max(1, int(d['position']))
    if 'paused' in d:
        p.paused = str(d['paused']).lower() in ('1', 'true')
    if p.ends_at and p.ends_at < p.starts_at:
        return Response({'detail': 'The end must be after the start.'}, status=400)
    p.save()
    _log(request.user, 'edited', shelf=p.shelf, story=p.story,
         note=', '.join(k for k in ('starts_at', 'ends_at', 'position', 'paused', 'end_now', 'extend_days') if k in d))
    return Response({'detail': 'Updated.', 'placement': _placement(request, p),
                     'warnings': _conflicts(p.shelf, p.story_id, p.position, p.starts_at, p.ends_at, exclude=p.pk)})


@api_view(['POST'])
@permission_classes([IsPromo])
def reorder(request, pk):
    """POST …/shelves/<id>/reorder/ {order: [placement_id, …]} — slot 1, 2, 3…"""
    shelf = get_object_or_404(Shelf, pk=pk)
    for pos, pid in enumerate(request.data.get('order') or [], 1):
        Placement.objects.filter(pk=pid, shelf=shelf).update(position=pos)
    _log(request.user, 'reordered', shelf=shelf)
    return Response({'detail': 'Order saved.'})


# ── Active list + calendar ────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsPromo])
def placements(request):
    """GET …/placements/?status=active|scheduled|paused|expired|all&shelf="""
    now = timezone.now()
    qs = Placement.objects.select_related('shelf', 'story__author', 'story__genre', 'created_by')
    st = request.query_params.get('status', 'active')
    if request.query_params.get('shelf'):
        qs = qs.filter(shelf_id=request.query_params['shelf'])
    live = Q(ends_at__isnull=True) | Q(ends_at__gt=now)
    if st == 'active':
        qs = qs.filter(live, cancelled=False, paused=False, starts_at__lte=now)
    elif st == 'scheduled':
        qs = qs.filter(cancelled=False, starts_at__gt=now)
    elif st == 'paused':
        qs = qs.filter(live, cancelled=False, paused=True)
    elif st == 'expired':
        qs = qs.filter(Q(ends_at__lte=now) | Q(cancelled=True)).order_by('-ends_at')
    return Response({'results': [_placement(request, p, now) for p in qs.order_by('shelf__order', 'position', 'starts_at')[:400]]})


@api_view(['GET'])
@permission_classes([IsPromo])
def calendar(request):
    """GET …/calendar/?start=YYYY-MM-DD&days=14 — what's on each shelf each
    day, plus clashes (two books in one slot, a book twice on a shelf,
    more books than slots)."""
    from datetime import date, datetime, time
    try:
        d0 = date.fromisoformat(request.query_params.get('start') or '')
    except ValueError:
        d0 = timezone.localdate()
    days = max(1, min(int(request.query_params.get('days', 14)), 62))
    start = timezone.make_aware(datetime.combine(d0, time.min))
    end = start + timedelta(days=days)
    qs = (Placement.objects.filter(cancelled=False, starts_at__lt=end).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=start))
          .select_related('shelf', 'story__author', 'story__genre', 'created_by'))
    rows = list(qs)
    out = []
    for i in range(days):
        a = start + timedelta(days=i)
        b = a + timedelta(days=1)
        on = [p for p in rows if p.starts_at < b and (p.ends_at is None or p.ends_at > a)]
        clashes = []
        by_shelf = defaultdict(list)
        for p in on:
            by_shelf[p.shelf_id].append(p)
        for sid, ps in by_shelf.items():
            shelf = ps[0].shelf
            slots = defaultdict(list)
            books = defaultdict(list)
            for p in ps:
                slots[p.position].append(p)
                books[p.story_id].append(p)
            for pos, same in slots.items():
                overl = [x for x in same if any(x is not y and x.starts_at < (y.ends_at or end) and y.starts_at < (x.ends_at or end) for y in same)]
                if overl:
                    clashes.append(f'{shelf.name}: slot {pos} is double-booked')
            for _, same in books.items():
                if len(same) > 1 and len({x.position for x in same}) > 1:
                    clashes.append(f'{shelf.name}: "{same[0].story.title}" appears twice')
            if len({p.position for p in ps}) > shelf.capacity:
                clashes.append(f'{shelf.name}: more books than its {shelf.capacity} slots')
        out.append({'date': a.date().isoformat(), 'placements': [_placement(request, p) for p in sorted(on, key=lambda p: (p.shelf.order, p.position))],
                    'clashes': sorted(set(clashes))})
    return Response({'start': d0.isoformat(), 'days': out})


# ── SE promotion requests (the team decides; the CE can too) ──────────────────

@api_view(['GET'])
@permission_classes([IsPromo])
def requests_list(request):
    """GET …/requests/?status=pending|approved|rejected|all"""
    from apps.editorial.models import SEPromotionRequest
    qs = SEPromotionRequest.objects.select_related('se', 'story__author', 'story__genre', 'reviewed_by').order_by('-created_at')
    st = request.query_params.get('status', 'pending')
    if st != 'all':
        qs = qs.filter(status=st)
    now = timezone.now()
    out = []
    for r in qs[:200]:
        ps = list(Placement.objects.filter(request=r, cancelled=False))
        stage = r.status
        if r.status == 'approved' and ps:
            stage = 'promoted' if any(p.starts_at <= now for p in ps) else 'scheduled'
        out.append({'id': r.id, 'book': _book(request, r.story, full=True), 'se': r.se.get_full_name() or r.se.username,
                    'reason': r.message, 'tab': r.tab, 'section': r.section, 'status': r.status, 'stage': stage,
                    'feedback': r.ce_note, 'reviewed_by': r.reviewed_by.username if r.reviewed_by_id else None,
                    'created_at': _iso(r.created_at), 'reviewed_at': _iso(r.reviewed_at)})
    return Response({'results': out})


@api_view(['POST'])
@permission_classes([IsPromo])
def request_review(request, pk):
    """POST …/requests/<id>/review/
    approve: {action: "approve", shelf_id, starts_at, days|ends_at, position}
    reject:  {action: "reject", feedback}"""
    from apps.editorial.models import SEPromotionRequest
    r = get_object_or_404(SEPromotionRequest.objects.select_related('se', 'story'), pk=pk)
    if r.status != 'pending':
        return Response({'detail': f'This request was already {r.status}.'}, status=400)
    action = request.data.get('action')
    now = timezone.now()
    if action == 'reject':
        fb = (request.data.get('feedback') or '').strip()
        if not fb:
            return Response({'detail': 'Give the senior editor a reason.'}, status=400)
        r.status, r.ce_note, r.reviewed_by, r.reviewed_at = 'rejected', fb, request.user, now
        r.save(update_fields=['status', 'ce_note', 'reviewed_by', 'reviewed_at'])
        _notify(r.se, f'Promotion request not approved: "{r.story.title}"', f'Feedback from the Promotion team: {fb}',
                {'promotion_request': r.id})
        _log(request.user, 'request_rejected', story=r.story, note=fb[:255])
        return Response({'detail': 'Rejected — the senior editor can see your feedback.'})
    if action != 'approve':
        return Response({'detail': 'Unknown action.'}, status=400)
    shelf = get_object_or_404(Shelf, pk=request.data.get('shelf_id'))
    starts = _when(request.data.get('starts_at')) or now
    ends = _when(request.data.get('ends_at')) or (starts + timedelta(days=float(request.data.get('days') or 7)))
    pos = int(request.data.get('position') or 1)
    Placement.objects.create(shelf=shelf, story=r.story, position=pos, starts_at=starts, ends_at=ends,
                             source=Placement.SOURCE_REQUEST, request=r, created_by=request.user,
                             label=f'Request from {r.se.username}')
    r.status, r.reviewed_by, r.reviewed_at = 'approved', request.user, now
    r.ce_note = (request.data.get('feedback') or '').strip()
    r.save(update_fields=['status', 'ce_note', 'reviewed_by', 'reviewed_at'])
    _notify(r.se, f'Promotion approved: "{r.story.title}"',
            f'On {shelf.name} from {timezone.localtime(starts):%d %b %H:%M} to {timezone.localtime(ends):%d %b %H:%M}.',
            {'promotion_request': r.id})
    _log(request.user, 'request_approved', shelf=shelf, story=r.story, note=f'slot {pos}, {starts:%d %b} → {ends:%d %b}')
    return Response({'detail': f'Approved — on {shelf.name} from {timezone.localtime(starts):%d %b %H:%M}.',
                     'warnings': _conflicts(shelf, r.story_id, pos, starts, ends)})


def _notify(user, title, message, data=None):
    try:
        from apps.notifications.services import create_notification
        create_notification(user, 'system', title, message, data=data or {}, send_push=False)
    except Exception:
        pass


# ── Overview + history ────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsPromo])
def overview(request):
    from apps.editorial.models import SEPromotionRequest
    from apps.promos.models import InAppPromo
    from apps.stories.models import PromoBanner
    Shelf.ensure_defaults()
    now = timezone.now()
    day_end = now + timedelta(hours=24)
    base = Placement.objects.filter(cancelled=False)
    live = base.filter(paused=False, starts_at__lte=now).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
    return Response({
        'requests': SEPromotionRequest.objects.filter(status='pending').count(),
        'live': live.count(),
        'books_live': live.values('story_id').distinct().count(),
        'starting_24h': base.filter(starts_at__gt=now, starts_at__lte=day_end).count(),
        'ending_24h': live.filter(ends_at__gt=now, ends_at__lte=day_end).count(),
        'paused': base.filter(paused=True).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).count(),
        'scheduled': base.filter(starts_at__gt=now).count(),
        'empty_shelves': [s.name for s in Shelf.objects.filter(is_active=True, group='Home')
                          if not live.filter(shelf=s).exists()],
        'banners': PromoBanner.objects.filter(is_active=True).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).count(),
        'popups': InAppPromo.objects.filter(is_active=True, starts_at__lte=now).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).count(),
    })


@api_view(['GET'])
@permission_classes([IsPromo])
def history(request):
    """GET …/history/?q= — every promotion action: shelf placements, SE
    requests, banners, pop-ups, social posts."""
    from .models import PromotionLog
    qs = PromotionLog.objects.select_related('user', 'shelf', 'story').order_by('-created_at')
    q = (request.query_params.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(story__title__icontains=q) | Q(shelf__name__icontains=q) | Q(user__username__icontains=q) | Q(note__icontains=q))
    return Response({'results': [{'at': _iso(l.created_at), 'by': l.user.username if l.user_id else '',
                                  'action': l.get_action_display(), 'shelf': l.shelf.name if l.shelf_id else '',
                                  'book': l.story.title if l.story_id else '', 'note': l.note} for l in qs[:300]]})
