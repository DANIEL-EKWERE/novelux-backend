"""/api/editorial/ce/promo-center/… — every promotional spot in the app, in
one place for the chief editor, each on a timeline (start → end, then the
spot frees up for the next book), plus a book's numbers before approving it.

Spots:
  slots    — home sections (Trending, Editor's Pick, Featured…)   StoryPromotion
  pins     — Explore tab sections (Werewolf → Fresh Reads…)       ExploreTabPin
  banners  — home carousel banners                                PromoBanner
  library  — library screen carousel                              Story.is_library_banner
  popups   — pop-up / full-screen on app open                     promos.InAppPromo (/promotions/)
"""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .permissions import IsCE

DEFAULT_DAYS = 7


def _when(value, default=None):
    if not value:
        return default
    dt = parse_datetime(str(value))
    if dt and timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt or default


def _window(data, default_days=DEFAULT_DAYS):
    """(starts, ends) from {starts_at, expires_at | ends_at | days}."""
    starts = _when(data.get('starts_at'), timezone.now())
    ends = _when(data.get('expires_at') or data.get('ends_at'))
    if not ends and data.get('days') not in (None, ''):
        try:
            ends = starts + timedelta(days=max(1, min(int(data.get('days')), 365)))
        except (TypeError, ValueError):
            ends = None
    if ends is None and default_days:
        ends = starts + timedelta(days=default_days)
    return starts, ends


def _state(starts, ends, active=True, now=None):
    now = now or timezone.now()
    if not active or (ends and ends <= now):
        return 'ended'
    if starts and starts > now:
        return 'upcoming'
    return 'live'


def _cover(request, story):
    try:
        return request.build_absolute_uri(story.cover_image.url) if story.cover_image else None
    except Exception:
        return None


def _book(request, s):
    return {'id': s.pk, 'slug': s.slug, 'title': s.title, 'author': s.author.username if s.author_id else '',
            'cover': _cover(request, s), 'views': s.total_views, 'rating': float(s.average_rating or 0)}


def _iso(dt):
    return dt.isoformat() if dt else None


# ── Overview + placements ─────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsCE])
def placements(request):
    """GET …/placements/?type=slots|pins|banners|library&state=live|upcoming|ended|all"""
    from apps.stories.models import PromoBanner, Story
    from .models import ExploreTabPin, StoryPromotion
    kind = request.query_params.get('type', 'slots')
    want = request.query_params.get('state', 'current')   # current = live + upcoming
    now = timezone.now()
    rows = []
    if kind == 'slots':
        qs = StoryPromotion.objects.select_related('story__author', 'se').order_by('category', 'starts_at')
        if want != 'all':
            qs = qs.filter(expires_at__gt=now - timedelta(days=30)) if want == 'ended' else qs.filter(expires_at__gt=now)
        for p in qs[:300]:
            st = 'queued' if p.status == StoryPromotion.STATUS_QUEUED else _state(
                p.starts_at, p.expires_at, p.status != StoryPromotion.STATUS_EXPIRED, now)
            rows.append({'id': p.pk, 'type': 'slots', 'spot': p.category, 'spot_label': p.get_category_display(),
                         'book': _book(request, p.story), 'by': p.se.username, 'starts_at': _iso(p.starts_at),
                         'ends_at': _iso(p.expires_at), 'state': st})
    elif kind == 'pins':
        from .views import TAB_SECTIONS
        names = {(t, s['slug']): s['name'] for t, secs in TAB_SECTIONS.items() for s in secs}
        qs = ExploreTabPin.objects.select_related('story__author', 'pinned_by').order_by('tab', 'section', 'order')
        for p in qs[:300]:
            starts = p.starts_at or p.pinned_at
            rows.append({'id': p.pk, 'type': 'pins', 'spot': f'{p.tab}/{p.section}',
                         'spot_label': f'{p.tab.replace("-", " ").title()} → {names.get((p.tab, p.section), p.section)}',
                         'book': _book(request, p.story), 'by': p.pinned_by.username if p.pinned_by_id else '',
                         'starts_at': _iso(starts), 'ends_at': _iso(p.expires_at), 'order': p.order,
                         'state': _state(starts, p.expires_at, p.is_active, now)})
    elif kind == 'banners':
        books = {s.slug: s for s in Story.objects.filter(
            slug__in=PromoBanner.objects.values_list('slug', flat=True)).select_related('author')}
        for b in PromoBanner.objects.order_by('order', '-created_at')[:200]:
            s = books.get(b.slug)
            rows.append({'id': b.pk, 'type': 'banners', 'spot': 'banner', 'spot_label': 'Home banner',
                         'title': b.title, 'image': b.get_image_url(request), 'color': b.color, 'order': b.order,
                         'book': _book(request, s) if s else None, 'slug': b.slug,
                         'starts_at': _iso(b.starts_at or b.created_at), 'ends_at': _iso(b.ends_at),
                         'state': _state(b.starts_at, b.ends_at, b.is_active, now)})
    elif kind == 'library':
        for s in Story.objects.filter(is_library_banner=True).select_related('author').order_by('-updated_at')[:50]:
            rows.append({'id': s.pk, 'type': 'library', 'spot': 'library', 'spot_label': 'Library carousel',
                         'book': _book(request, s), 'starts_at': None, 'ends_at': None, 'state': 'live'})
    else:
        return Response({'detail': 'Unknown type.'}, status=400)
    if want in ('live', 'upcoming', 'ended'):
        rows = [r for r in rows if r['state'] == want or (want == 'upcoming' and r['state'] == 'queued')]
    elif want == 'current':
        rows = [r for r in rows if r['state'] != 'ended']
    return Response({'results': rows})


@api_view(['GET'])
@permission_classes([IsCE])
def overview(request):
    """Counts for the Promotions tabs."""
    from apps.promos.models import InAppPromo
    from apps.stories.models import PromoBanner, Story
    from .models import ExploreTabPin, SEPromotionRequest, StoryPromotion
    now = timezone.now()
    live_pins = (ExploreTabPin.objects.filter(is_active=True)
                 .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
                 .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).count())
    return Response({
        'requests': SEPromotionRequest.objects.filter(status='pending').count(),
        'slots': StoryPromotion.objects.filter(status=StoryPromotion.STATUS_ACTIVE, starts_at__lte=now,
                                               expires_at__gt=now).count(),
        'queued': StoryPromotion.objects.filter(status=StoryPromotion.STATUS_QUEUED).count(),
        'pins': live_pins,
        'banners': PromoBanner.objects.filter(is_active=True).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).count(),
        'library': Story.objects.filter(is_library_banner=True).count(),
        'popups': InAppPromo.objects.filter(is_active=True, starts_at__lte=now).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gt=now)).count(),
        'ending_soon': StoryPromotion.objects.filter(status=StoryPromotion.STATUS_ACTIVE, expires_at__gt=now,
                                                     expires_at__lte=now + timedelta(days=2)).count(),
    })


# ── Section slots (home sections) ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsCE])
def add_slot(request):
    """POST …/slots/ {story_id, category, starts_at?, days? | expires_at?}
    The chief editor places a book directly (no slot limit)."""
    from apps.stories.models import Story
    from .models import StoryPromotion
    story = get_object_or_404(Story, pk=request.data.get('story_id'))
    category = request.data.get('category', '')
    if category not in dict(StoryPromotion._meta.get_field('category').choices):
        return Response({'detail': 'Choose a section.'}, status=400)
    starts, ends = _window(request.data)
    if ends <= starts:
        return Response({'detail': 'The end must be after the start.'}, status=400)
    p = StoryPromotion.objects.create(se=request.user, story=story, category=category, starts_at=starts,
                                      expires_at=ends, status=StoryPromotion.STATUS_ACTIVE)
    return Response({'detail': f'"{story.title}" placed in {p.get_category_display()} '
                               f'until {ends:%d %b}.', 'id': p.pk}, status=201)


def _set_end(obj, field, data, start_field=None):
    """end_now / days (from now) / expires_at — shared by slots, pins, banners."""
    now = timezone.now()
    if str(data.get('end_now', '')).lower() in ('1', 'true'):
        setattr(obj, field, now)
        return None
    if data.get('extend_days') not in (None, ''):
        try:
            cur = getattr(obj, field) or now
            setattr(obj, field, max(cur, now) + timedelta(days=int(data['extend_days'])))
        except (TypeError, ValueError):
            return 'Days must be a number.'
        return None
    if 'expires_at' in data or 'ends_at' in data:
        setattr(obj, field, _when(data.get('expires_at') or data.get('ends_at')))
    if start_field and data.get('starts_at'):
        setattr(obj, start_field, _when(data.get('starts_at')))
    return None


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsCE])
def slot_detail(request, pk):
    from .models import StoryPromotion
    p = get_object_or_404(StoryPromotion, pk=pk)
    if request.method == 'DELETE':
        p.delete()
        return Response({'detail': 'Removed.'})
    err = _set_end(p, 'expires_at', request.data, 'starts_at')
    if err:
        return Response({'detail': err}, status=400)
    if p.expires_at and p.expires_at <= timezone.now():
        p.status = StoryPromotion.STATUS_EXPIRED
    elif p.status == StoryPromotion.STATUS_EXPIRED:
        p.status = StoryPromotion.STATUS_ACTIVE
    p.save()
    return Response({'detail': 'Updated.'})


# ── Explore tab pins ──────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsCE])
def add_pin(request):
    """POST …/pins/ {story_id, tab, section, starts_at?, days?, order?}"""
    from apps.stories.models import Story
    from .models import ExploreTabPin
    from .views import TAB_SECTIONS
    story = get_object_or_404(Story, pk=request.data.get('story_id'))
    tab, section = request.data.get('tab', ''), request.data.get('section', '')
    if section not in {s['slug'] for s in TAB_SECTIONS.get(tab, [])}:
        return Response({'detail': 'Choose a tab and section.'}, status=400)
    starts, ends = _window(request.data)
    pin, _ = ExploreTabPin.objects.update_or_create(
        tab=tab, section=section, story=story,
        defaults={'pinned_by': request.user, 'is_active': True, 'starts_at': starts, 'expires_at': ends,
                  'order': int(request.data.get('order') or 0)})
    return Response({'detail': f'"{story.title}" pinned until {ends:%d %b}.', 'id': pin.pk}, status=201)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsCE])
def pin_detail(request, pk):
    from .models import ExploreTabPin
    p = get_object_or_404(ExploreTabPin, pk=pk)
    if request.method == 'DELETE':
        p.delete()
        return Response({'detail': 'Removed.'})
    err = _set_end(p, 'expires_at', request.data, 'starts_at')
    if err:
        return Response({'detail': err}, status=400)
    if 'order' in request.data:
        p.order = int(request.data.get('order') or 0)
    if p.expires_at is None or p.expires_at > timezone.now():
        p.is_active = True
    p.save()
    return Response({'detail': 'Updated.'})


# ── Home banners ──────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsCE])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def add_banner(request):
    """POST …/banners/ (multipart) {title, slug, image, color, order, starts_at, days|ends_at}"""
    from apps.stories.models import PromoBanner, Story
    title = (request.data.get('title') or '').strip()
    slug = (request.data.get('slug') or '').strip()
    if not title:
        return Response({'detail': 'Give the banner a title.'}, status=400)
    if slug and not Story.objects.filter(slug=slug).exists():
        return Response({'detail': 'That book was not found.'}, status=400)
    img = request.FILES.get('image')
    if img and (img.size > 8 * 1024 * 1024 or not (img.content_type or '').startswith('image/')):
        return Response({'detail': 'Upload a picture up to 8 MB.'}, status=400)
    starts, ends = _window(request.data, default_days=None)
    b = PromoBanner.objects.create(title=title[:200], slug=slug, image=img, color=request.data.get('color') or '#C15F3C',
                                   order=int(request.data.get('order') or 0), starts_at=starts, ends_at=ends)
    return Response({'detail': 'Banner added.', 'id': b.pk}, status=201)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsCE])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def banner_detail(request, pk):
    from apps.stories.models import PromoBanner
    b = get_object_or_404(PromoBanner, pk=pk)
    if request.method == 'DELETE':
        b.delete()
        return Response({'detail': 'Removed.'})
    err = _set_end(b, 'ends_at', request.data, 'starts_at')
    if err:
        return Response({'detail': err}, status=400)
    for f in ('title', 'color'):
        if request.data.get(f):
            setattr(b, f, request.data[f])
    if 'order' in request.data:
        b.order = int(request.data.get('order') or 0)
    if 'is_active' in request.data:
        b.is_active = str(request.data['is_active']).lower() in ('1', 'true')
    if request.FILES.get('image'):
        b.image = request.FILES['image']
    b.save()
    return Response({'detail': 'Updated.'})


# ── Library carousel ──────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsCE])
def library_toggle(request, pk):
    """POST …/library/<story id>/ {on: true|false}"""
    from apps.stories.models import Story
    s = get_object_or_404(Story, pk=pk)
    s.is_library_banner = str(request.data.get('on', 'true')).lower() in ('1', 'true')
    s.save(update_fields=['is_library_banner'])
    return Response({'detail': f'"{s.title}" {"added to" if s.is_library_banner else "removed from"} the library carousel.'})


# ── Book search + insights ────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsCE])
def books(request):
    from apps.stories.models import Story
    q = (request.query_params.get('q') or '').strip()
    qs = Story.objects.exclude(status__in=['draft', 'rejected']).select_related('author').order_by('-total_views')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(author__username__icontains=q))
    return Response([_book(request, s) for s in qs[:12]])


@api_view(['GET'])
@permission_classes([IsCE])
def book_insights(request, slug):
    """GET …/insights/<slug>/ — how a book performs, to judge it before
    promoting: reach, how far readers get, money, quality signals, and a
    0–100 promotion score."""
    from apps.chapters.models import Chapter, ChapterUnlock
    from apps.coins.models import ReadingHistory
    from apps.stories.models import ContentReport, Story
    from .models import ContentFlag, ExploreTabPin, StoryPromotion
    s = get_object_or_404(Story.objects.select_related('author', 'genre'), slug=slug)
    now = timezone.now()
    published = Chapter.objects.filter(story=s, is_published=True)
    last_ch = published.order_by('-chapter_number').values_list('chapter_number', flat=True).first() or 0
    hist = ReadingHistory.objects.filter(story=s)
    readers = hist.count()

    def reached(n):
        return hist.filter(chapter_number__gte=n).count()
    funnel = [{'chapter': n, 'readers': reached(n)} for n in sorted({1, 3, 5, 10, 20, last_ch}) if 0 < n <= max(last_ch, 1)]
    finished = reached(last_ch) if last_ch else 0
    completion = round(finished / readers * 100, 1) if readers else 0
    unlocks = ChapterUnlock.objects.filter(chapter__story=s).aggregate(n=Count('id'), coins=Sum('coins_spent'))
    week = hist.filter(read_at__gte=now - timedelta(days=7)).count()
    month = hist.filter(read_at__gte=now - timedelta(days=30)).count()
    reports_open = ContentReport.objects.filter(story=s, status='pending').count()
    flags_open = ContentFlag.objects.filter(chapter__story=s, resolved=False).count()
    engagement = round(((s.total_likes or 0) + (s.total_comments or 0)) / s.total_views * 100, 1) if s.total_views else 0
    days_since_update = (now - published.order_by('-created_at').values_list('created_at', flat=True).first()).days \
        if published.exists() else None

    # Promotion score — a guide, not a verdict
    rating = float(s.average_rating or 0)
    score = 0
    score += min(completion, 60) / 60 * 30                                  # readers finish it
    score += (rating / 5 * 20) if s.total_ratings >= 3 else 8               # readers like it
    score += min(engagement, 10) / 10 * 15                                  # likes + comments per view
    score += min((unlocks['n'] or 0) / max(readers, 1), 3) / 3 * 15         # readers pay to continue
    score += 10 if days_since_update is not None and days_since_update <= 14 else (5 if days_since_update and days_since_update <= 45 else 0)
    score += 10 if not (reports_open or flags_open) else 0
    score = round(score)
    verdict = 'Strong' if score >= 65 else 'Good' if score >= 45 else 'Weak'
    notes = []
    if readers < 20:
        notes.append('Few readers so far — numbers are early.')
    if completion < 15 and readers >= 20:
        notes.append('Most readers stop early — check the opening chapters.')
    if s.total_ratings and rating < 3.5:
        notes.append('Below-average rating.')
    if reports_open or flags_open:
        notes.append(f'{reports_open + flags_open} open report(s)/flag(s) — resolve before promoting.')
    if days_since_update is not None and days_since_update > 30:
        notes.append(f'No new chapter in {days_since_update} days.')
    if s.is_explicit:
        notes.append('Marked explicit — hidden from readers when explicit content is off.')

    history = [{'spot': p.get_category_display(), 'starts_at': _iso(p.starts_at), 'ends_at': _iso(p.expires_at)}
               for p in StoryPromotion.objects.filter(story=s).order_by('-starts_at')[:5]]
    history += [{'spot': f'{p.tab} → {p.section}', 'starts_at': _iso(p.starts_at or p.pinned_at),
                 'ends_at': _iso(p.expires_at)} for p in ExploreTabPin.objects.filter(story=s)[:5]]
    return Response({
        'book': {**_book(request, s), 'genre': s.genre.name if s.genre_id else '', 'status': s.status,
                 'contract_status': s.contract_status, 'chapters': published.count(), 'words': s.word_count,
                 'created_at': _iso(s.created_at)},
        'reach': {'views': s.total_views, 'readers': readers, 'active_7d': week, 'active_30d': month,
                  'likes': s.total_likes, 'comments': s.total_comments, 'engagement_pct': engagement},
        'reading': {'funnel': funnel, 'finished': finished, 'completion_pct': completion,
                    'days_since_update': days_since_update},
        'quality': {'rating': rating, 'ratings': s.total_ratings, 'reports_open': reports_open,
                    'flags_open': flags_open},
        'money': {'unlocks': unlocks['n'] or 0, 'coins': unlocks['coins'] or 0, 'tips': s.total_tips},
        'score': score, 'verdict': verdict, 'notes': notes, 'history': history,
    })
