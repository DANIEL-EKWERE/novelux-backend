"""/api/social/… — the team's social posting dashboard."""
import json

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import PLATFORMS, TEXT_LIMITS, SocialAccount, SocialMedia, SocialPost, SocialPostTarget, SocialSettings
from .publishers import PUBLISHERS
from .service import can_manage, can_post, check_lengths, needs_approval, publish_in_background

MAX_MB = {'image': 15, 'video': 250}


class CanPost(BasePermission):
    message = 'Posting to social media is for the editorial team and admins.'

    def has_permission(self, request, view):
        return can_post(request.user)


def _manage_only(request):
    if not can_manage(request.user):
        return Response({'detail': 'Only admins can do this.'}, status=403)


def _iso(dt):
    return dt.isoformat() if dt else None


def _account(a, manage):
    d = {'id': a.pk, 'platform': a.platform, 'platform_name': a.get_platform_display(), 'name': a.name,
         'handle': a.handle, 'is_active': a.is_active, 'last_error': a.last_error,
         'last_checked': _iso(a.last_checked), 'text_limit': TEXT_LIMITS.get(a.platform)}
    if manage:
        d['config'] = a.config
        # Which secrets are set — never their values
        d['secrets_set'] = sorted(k for k, v in a.secrets.items() if v)
    return d


def _post(request, p):
    return {
        'id': p.pk, 'text': p.text, 'link': p.link, 'title': p.title, 'status': p.status,
        'author': p.author.username if p.author_id else None,
        'story': {'title': p.story.title, 'slug': p.story.slug} if p.story_id else None,
        'scheduled_at': _iso(p.scheduled_at), 'created_at': _iso(p.created_at),
        'published_at': _iso(p.published_at),
        'approved_by': p.approved_by.username if p.approved_by_id else None, 'review_note': p.review_note,
        'media': [{'id': m.pk, 'kind': m.kind, 'url': request.build_absolute_uri(m.file.url)} for m in p.media.all()],
        'targets': [{'id': t.pk, 'account_id': t.account_id, 'account': t.account.name,
                     'platform': t.account.platform, 'status': t.status, 'url': t.url, 'error': t.error,
                     'text': t.text, 'published_at': _iso(t.published_at)} for t in p.targets.all()],
    }


@api_view(['GET'])
@permission_classes([CanPost])
def overview(request):
    """Accounts, settings, what this user may do, and the setup fields per network."""
    manage = can_manage(request.user)
    s = SocialSettings.get()
    return Response({
        'can_manage': manage,
        'needs_approval': needs_approval(request.user),
        'settings': {'require_approval': s.require_approval, 'poster_roles': s.poster_roles},
        'accounts': [_account(a, manage) for a in SocialAccount.objects.all()],
        'platforms': [{'id': k, 'name': n, 'text_limit': TEXT_LIMITS.get(k),
                       'fields': [{'key': f, 'label': lbl, 'secret': sec} for f, lbl, sec in PUBLISHERS[k].fields]}
                      for k, n in PLATFORMS],
        'pending_count': SocialPost.objects.filter(status=SocialPost.STATUS_PENDING).count(),
    })


@api_view(['PATCH'])
@permission_classes([CanPost])
def update_settings(request):
    if (r := _manage_only(request)):
        return r
    s = SocialSettings.get()
    if 'require_approval' in request.data:
        s.require_approval = bool(request.data['require_approval'])
    if 'poster_roles' in request.data:
        s.poster_roles = [x for x in request.data['poster_roles'] if x in ('se', 'ce', 'author')]
    s.save()
    return Response({'require_approval': s.require_approval, 'poster_roles': s.poster_roles})


def _apply_account_fields(acc, data):
    fields = PUBLISHERS[acc.platform].fields
    config, secrets = dict(acc.config), {}
    incoming = data.get('values') or {}
    for key, _label, secret in fields:
        val = str(incoming.get(key, '') or '').strip()
        if not val:
            continue  # blank = keep what's stored
        (secrets if secret else config).__setitem__(key, val)
    acc.config = config
    if secrets:
        acc.update_secrets(**secrets)


@api_view(['GET', 'POST'])
@permission_classes([CanPost])
def accounts(request):
    if request.method == 'GET':
        return Response([_account(a, can_manage(request.user)) for a in SocialAccount.objects.all()])
    if (r := _manage_only(request)):
        return r
    platform = request.data.get('platform')
    if platform not in PUBLISHERS:
        return Response({'detail': 'Unknown network.'}, status=400)
    acc = SocialAccount(platform=platform, name=(request.data.get('name') or dict(PLATFORMS)[platform])[:120],
                        connected_by=request.user)
    _apply_account_fields(acc, request.data)
    acc.save()
    return Response(_account(acc, True), status=201)


@api_view(['PATCH', 'DELETE'])
@permission_classes([CanPost])
def account_detail(request, pk):
    if (r := _manage_only(request)):
        return r
    acc = get_object_or_404(SocialAccount, pk=pk)
    if request.method == 'DELETE':
        acc.delete()
        return Response(status=204)
    if 'name' in request.data:
        acc.name = str(request.data['name'])[:120]
    if 'is_active' in request.data:
        acc.is_active = bool(request.data['is_active'])
    _apply_account_fields(acc, request.data)
    acc.save()
    return Response(_account(acc, True))


@api_view(['POST'])
@permission_classes([CanPost])
def account_test(request, pk):
    """Checks the connection with a harmless read (nothing is posted)."""
    if (r := _manage_only(request)):
        return r
    acc = get_object_or_404(SocialAccount, pk=pk)
    try:
        who = PUBLISHERS[acc.platform].verify(acc)
        acc.handle, acc.last_error, ok = str(who)[:120], '', True
    except Exception as e:
        acc.last_error, ok, who = str(e)[:1000], False, str(e)
    acc.last_checked = timezone.now()
    acc.save(update_fields=['handle', 'last_error', 'last_checked'])
    return Response({'ok': ok, 'message': who, 'account': _account(acc, True)})


@api_view(['GET'])
@permission_classes([CanPost])
def books(request):
    """Books to promote: title, cover, synopsis and the share link."""
    from apps.stories.models import Story
    q = (request.query_params.get('q') or '').strip()
    qs = Story.objects.select_related('author').order_by('-total_views')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(author__username__icontains=q))
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    out = []
    for s in qs[:12]:
        cover = None
        try:
            cover = request.build_absolute_uri(s.cover_image.url) if s.cover_image else None
        except Exception:
            pass
        out.append({'id': s.pk, 'title': s.title, 'slug': s.slug, 'author': s.author.username, 'cover': cover,
                    'synopsis': (s.description or s.synopsis or '')[:600], 'link': f'{site}/explore/{s.slug}/'})
    return Response(out)


@api_view(['GET', 'POST'])
@permission_classes([CanPost])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def posts(request):
    if request.method == 'GET':
        qs = SocialPost.objects.select_related('author', 'story', 'approved_by').prefetch_related(
            'media', 'targets__account')
        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        if not can_manage(request.user) and request.query_params.get('mine'):
            qs = qs.filter(author=request.user)
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1
        total = qs.count()
        return Response({'total': total, 'page': page, 'pages': (total + 19) // 20,
                         'results': [_post(request, p) for p in qs[(page - 1) * 20: page * 20]]})

    # ── Create ──
    d = request.data
    action = d.get('action', 'publish')          # publish | schedule | draft
    ids = d.getlist('account_ids') if hasattr(d, 'getlist') else d.get('account_ids', [])
    ids = [int(x) for x in ids if str(x).isdigit()]
    accs = list(SocialAccount.objects.filter(pk__in=ids, is_active=True))
    if not accs and action != 'draft':
        return Response({'detail': 'Choose at least one account to post to.'}, status=400)
    text = (d.get('text') or '').strip()
    files = request.FILES.getlist('files') if hasattr(request, 'FILES') else []
    if not text and not files and not d.get('use_cover'):
        return Response({'detail': 'Write something or add a picture or video.'}, status=400)
    for f in files:
        kind = 'video' if (f.content_type or '').startswith('video') else 'image'
        if not (f.content_type or '').startswith(('image', 'video')):
            return Response({'detail': f'"{f.name}" is not an image or video.'}, status=400)
        if f.size > MAX_MB[kind] * 1024 * 1024:
            return Response({'detail': f'"{f.name}" is over {MAX_MB[kind]} MB.'}, status=400)
    scheduled = None
    if action == 'schedule':
        scheduled = parse_datetime(d.get('scheduled_at') or '')
        if not scheduled:
            return Response({'detail': 'Pick a date and time to schedule the post.'}, status=400)
        if timezone.is_naive(scheduled):
            scheduled = timezone.make_aware(scheduled)
        if scheduled <= timezone.now():
            return Response({'detail': 'The scheduled time is in the past.'}, status=400)
    try:
        overrides = json.loads(d.get('overrides') or '{}')
    except ValueError:
        overrides = {}

    from apps.stories.models import Story
    story = Story.objects.filter(pk=d.get('story_id')).first() if str(d.get('story_id') or '').isdigit() else None
    post = SocialPost.objects.create(author=request.user, text=text, link=(d.get('link') or '').strip(),
                                     title=(d.get('title') or '')[:100], story=story, scheduled_at=scheduled)
    for i, f in enumerate(files):
        SocialMedia.objects.create(post=post, file=f, order=i,
                                   kind='video' if (f.content_type or '').startswith('video') else 'image')
    if str(d.get('use_cover', '')).lower() in ('1', 'true', 'on') and story and story.cover_image:
        # The book's cover, already in storage — no need to upload it again
        SocialMedia.objects.create(post=post, file=story.cover_image.name, order=len(files), kind='image')
    for a in accs:
        SocialPostTarget.objects.create(post=post, account=a, text=str(overrides.get(str(a.pk), '') or ''))

    problems = check_lengths(post)
    if problems and action != 'draft':
        post.delete()
        return Response({'detail': 'Too long for: ' + '; '.join(f'{n} ({m})' for n, m in problems)}, status=400)

    if action == 'draft':
        post.status = SocialPost.STATUS_DRAFT
    elif needs_approval(request.user):
        post.status = SocialPost.STATUS_PENDING
    elif action == 'schedule':
        post.status = SocialPost.STATUS_SCHEDULED
    else:
        post.status = SocialPost.STATUS_PUBLISHING   # going out now
    post.save(update_fields=['status'])
    if post.status == SocialPost.STATUS_PUBLISHING:
        publish_in_background(post.pk)
    post.refresh_from_db()
    return Response(_post(request, post), status=201)


@api_view(['GET', 'DELETE'])
@permission_classes([CanPost])
def post_detail(request, pk):
    post = get_object_or_404(SocialPost, pk=pk)
    if request.method == 'DELETE':
        if post.status in (SocialPost.STATUS_PUBLISHING, SocialPost.STATUS_PUBLISHED, SocialPost.STATUS_PARTIAL):
            return Response({'detail': "Published posts stay in the history (delete them on the network itself)."},
                            status=400)
        if post.author_id != request.user.pk and not can_manage(request.user):
            return Response({'detail': 'You can only delete your own posts.'}, status=403)
        post.delete()
        return Response(status=204)
    return Response(_post(request, post))


@api_view(['POST'])
@permission_classes([CanPost])
def post_action(request, pk, action):
    """approve | reject (admins) · retry | send_now | cancel (author or admin)."""
    post = get_object_or_404(SocialPost, pk=pk)
    mine = post.author_id == request.user.pk or can_manage(request.user)
    if action in ('approve', 'reject'):
        if (r := _manage_only(request)):
            return r
        if post.status != SocialPost.STATUS_PENDING:
            return Response({'detail': 'This post is not waiting for approval.'}, status=400)
        post.approved_by, post.approved_at = request.user, timezone.now()
        post.review_note = (request.data.get('note') or '')[:1000]
        if action == 'reject':
            post.status = SocialPost.STATUS_REJECTED
            post.save()
        else:
            now_due = not post.scheduled_at or post.scheduled_at <= timezone.now()
            post.status = SocialPost.STATUS_PUBLISHING if now_due else SocialPost.STATUS_SCHEDULED
            post.save()
            if now_due:
                publish_in_background(post.pk)
    elif action == 'retry':
        if not mine or post.status not in (SocialPost.STATUS_FAILED, SocialPost.STATUS_PARTIAL):
            return Response({'detail': 'Only failed posts can be retried.'}, status=400)
        post.targets.filter(status__in=['failed', 'skipped']).update(status='waiting', error='')
        post.status = SocialPost.STATUS_PUBLISHING
        post.save(update_fields=['status'])
        publish_in_background(post.pk)
    elif action == 'send_now':
        if not mine or post.status not in (SocialPost.STATUS_SCHEDULED, SocialPost.STATUS_DRAFT):
            return Response({'detail': 'Only scheduled posts and drafts can be sent now.'}, status=400)
        if post.status == SocialPost.STATUS_DRAFT and needs_approval(request.user):
            post.status = SocialPost.STATUS_PENDING
            post.save(update_fields=['status'])
        else:
            post.scheduled_at = None
            post.status = SocialPost.STATUS_PUBLISHING
            post.save(update_fields=['scheduled_at', 'status'])
            publish_in_background(post.pk)
    elif action == 'cancel':
        if not mine or post.status not in (SocialPost.STATUS_SCHEDULED, SocialPost.STATUS_PENDING):
            return Response({'detail': 'Only scheduled or waiting posts can be cancelled.'}, status=400)
        post.status = SocialPost.STATUS_DRAFT
        post.save(update_fields=['status'])
    else:
        return Response({'detail': 'Unknown action.'}, status=400)
    post.refresh_from_db()
    return Response(_post(request, post))
