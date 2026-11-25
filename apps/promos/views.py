"""/api/promos/… — book promotions shown when the app opens."""
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from .models import InAppPromo, PromoView

MAX_IMAGE_MB = 8


def can_manage(user):
    return bool(user and user.is_authenticated and
                (user.is_superuser or getattr(user, 'role', '') in ('admin', 'ce', 'se', 'promo')))


def can_edit(user, promo):
    """Admins and chief editors edit any promotion; senior editors their own."""
    if not can_manage(user):
        return False
    return user.is_superuser or user.role in ('admin', 'ce', 'promo') or promo.created_by_id == user.pk


class CanManage(BasePermission):
    message = 'Promotions are managed by admins and editors.'

    def has_permission(self, request, view):
        return can_manage(request.user)


def _abs(request, f):
    try:
        return request.build_absolute_uri(f.url) if f else None
    except Exception:
        return None


def _story(request, s):
    return {'id': s.pk, 'slug': s.slug, 'title': s.title, 'author': s.author.username if s.author_id else '',
            'cover': _abs(request, s.cover_image)}


def _public(request, p):
    return {'id': p.id, 'kind': p.kind, 'image': _abs(request, p.image), 'tagline': p.tagline,
            'button_text': p.button_text or 'View more', 'skip_seconds': p.skip_seconds,
            'story': _story(request, p.story)}


def _manage(request, p):
    return {**_public(request, p), 'name': p.name, 'starts_at': p.starts_at.isoformat(),
            'ends_at': p.ends_at.isoformat() if p.ends_at else None, 'is_active': p.is_active,
            'live': p.is_live(), 'priority': p.priority, 'impressions': p.impressions, 'clicks': p.clicks,
            'created_by': p.created_by.username if p.created_by_id else None,
            'can_edit': can_edit(request.user, p), 'created_at': p.created_at.isoformat()}


# ── App ───────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def next_promo(request):
    """GET /api/promos/next/?seen=3,5 — the one promotion to show on this app
    launch (or {"promo": null}). `seen` lists ids this device has already
    shown, for readers who aren't signed in."""
    from apps.stories.models import explicit_blocked
    now = timezone.now()
    qs = (InAppPromo.objects.filter(is_active=True, starts_at__lte=now)
          .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
          .exclude(story__status='draft').select_related('story__author'))
    seen = [int(x) for x in (request.query_params.get('seen') or '').split(',') if x.strip().isdigit()]
    if seen:
        qs = qs.exclude(pk__in=seen)
    if request.user.is_authenticated:
        qs = qs.exclude(views__user=request.user)
    for p in qs[:10]:
        if p.kind == InAppPromo.KIND_SPLASH and not p.image:
            continue            # a full-screen promo needs its poster
        if explicit_blocked(p.story, request.user, request):
            continue
        return Response({'promo': _public(request, p)})
    return Response({'promo': None})


@api_view(['POST'])
@permission_classes([AllowAny])
def promo_event(request, pk, event):
    """POST /api/promos/<id>/seen/ | /click/"""
    p = get_object_or_404(InAppPromo, pk=pk)
    user = request.user if request.user.is_authenticated else None
    if event == 'seen':
        InAppPromo.objects.filter(pk=pk).update(impressions=F('impressions') + 1)
        if user:
            PromoView.objects.get_or_create(promo=p, user=user)
    elif event == 'click':
        InAppPromo.objects.filter(pk=pk).update(clicks=F('clicks') + 1)
        if user:
            v, _ = PromoView.objects.get_or_create(promo=p, user=user)
            if not v.clicked_at:
                PromoView.objects.filter(pk=v.pk).update(clicked_at=timezone.now())
    else:
        return Response({'detail': 'Unknown event.'}, status=404)
    return Response({'ok': True})


# ── Dashboard (/promotions/) ──────────────────────────────────────────────────

def _apply(p, data, files):
    """Copy form fields onto a promotion. Returns an error message or None."""
    from apps.stories.models import Story
    if 'story_id' in data:
        story = Story.objects.filter(pk=data.get('story_id')).first()
        if not story:
            return 'Choose a book to promote.'
        p.story = story
    if 'kind' in data:
        if data['kind'] not in (InAppPromo.KIND_SPLASH, InAppPromo.KIND_POPUP):
            return 'Unknown promotion style.'
        p.kind = data['kind']
    for f, n in (('name', 120), ('tagline', 140), ('button_text', 30)):
        if f in data:
            setattr(p, f, str(data.get(f) or '').strip()[:n])
    if 'skip_seconds' in data:
        try:
            p.skip_seconds = max(1, min(int(data['skip_seconds']), 15))
        except (TypeError, ValueError):
            return 'Countdown must be a number of seconds.'
    if 'priority' in data:
        try:
            p.priority = int(data['priority'] or 0)
        except (TypeError, ValueError):
            pass
    for f in ('starts_at', 'ends_at'):
        if f in data:
            v = data.get(f)
            dt = parse_datetime(v) if v else None
            if v and not dt:
                return 'Use a valid date and time.'
            if dt and timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            if f == 'starts_at':
                p.starts_at = dt or timezone.now()
            else:
                p.ends_at = dt
    if 'is_active' in data:
        p.is_active = str(data['is_active']).lower() in ('1', 'true', 'on', 'yes')
    if files.get('image'):
        img = files['image']
        if img.size > MAX_IMAGE_MB * 1024 * 1024:
            return f'The image is over {MAX_IMAGE_MB} MB.'
        if not (img.content_type or '').startswith('image/'):
            return 'Upload a picture (JPG, PNG or WebP).'
        p.image = img
    elif str(data.get('remove_image', '')).lower() in ('1', 'true'):
        p.image = None
    if p.ends_at and p.ends_at <= p.starts_at:
        return 'The end must be after the start.'
    if p.kind == InAppPromo.KIND_SPLASH and not p.image:
        return 'A full-screen promotion needs a poster image.'
    return None


@api_view(['GET', 'POST'])
@permission_classes([CanManage])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def manage(request):
    if request.method == 'GET':
        qs = InAppPromo.objects.select_related('story__author', 'created_by')
        status = request.query_params.get('status')
        now = timezone.now()
        if status == 'live':
            qs = qs.filter(is_active=True, starts_at__lte=now).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        elif status == 'scheduled':
            qs = qs.filter(is_active=True, starts_at__gt=now)
        elif status == 'ended':
            qs = qs.filter(Q(is_active=False) | Q(ends_at__lte=now))
        return Response({'results': [_manage(request, p) for p in qs[:200]],
                         'me': {'can_edit_all': request.user.is_superuser or request.user.role in ('admin', 'ce')}})
    p = InAppPromo(created_by=request.user)
    if not request.data.get('story_id'):
        return Response({'detail': 'Choose a book to promote.'}, status=400)
    err = _apply(p, request.data, request.FILES)
    if err:
        return Response({'detail': err}, status=400)
    p.save()
    return Response(_manage(request, p), status=201)


@api_view(['PATCH', 'DELETE'])
@permission_classes([CanManage])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def manage_detail(request, pk):
    p = get_object_or_404(InAppPromo.objects.select_related('story__author'), pk=pk)
    if not can_edit(request.user, p):
        return Response({'detail': 'Only admins, chief editors or its creator can change this.'}, status=403)
    if request.method == 'DELETE':
        p.delete()
        return Response(status=204)
    err = _apply(p, request.data, request.FILES)
    if err:
        return Response({'detail': err}, status=400)
    p.save()
    return Response(_manage(request, p))


@api_view(['GET'])
@permission_classes([CanManage])
def books(request):
    """Books to promote (live ones only)."""
    from apps.stories.models import Story
    q = (request.query_params.get('q') or '').strip()
    qs = Story.objects.exclude(status='draft').select_related('author').order_by('-total_views')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(author__username__icontains=q))
    return Response([{**_story(request, s), 'synopsis': (s.description or '')[:200]} for s in qs[:12]])
