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
from .service import (can_manage, can_post, can_review, can_review_post, check_lengths, needs_approval,
                      notify_review_needed, notify_reviewed, publish_in_background)

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
        'author': p.author.username if p.author_id else None, 'author_id': p.author_id,
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
        'can_review': can_review(request.user),
        'me_id': request.user.pk,
        'needs_approval': needs_approval(request.user),
        'settings': {'require_approval': s.require_approval, 'ce_can_review': s.ce_can_review,
                     'poster_roles': s.poster_roles},
        'accounts': [_account(a, manage) for a in SocialAccount.objects.all()],
        'platforms': [{'id': k, 'name': n, 'text_limit': TEXT_LIMITS.get(k),
                       'fields': [{'key': f, 'label': lbl, 'secret': sec} for f, lbl, sec in PUBLISHERS[k].fields]}
                      for k, n in PLATFORMS],
        'pending_count': SocialPost.objects.filter(status=SocialPost.STATUS_PENDING).count(),
        'open_comments': _open_comments(),
    })


def _open_comments():
    from .models import SocialComment
    return SocialComment.objects.filter(is_ours=False, parent__isnull=True, handled=False).count()


@api_view(['PATCH'])
@permission_classes([CanPost])
def update_settings(request):
    if (r := _manage_only(request)):
        return r
    s = SocialSettings.get()
    if 'require_approval' in request.data:
        s.require_approval = bool(request.data['require_approval'])
    if 'ce_can_review' in request.data:
        s.ce_can_review = bool(request.data['ce_can_review'])
    if 'poster_roles' in request.data:
        s.poster_roles = [x for x in request.data['poster_roles'] if x in ('se', 'ce', 'author')]
    s.save()
    return Response({'require_approval': s.require_approval, 'ce_can_review': s.ce_can_review,
                     'poster_roles': s.poster_roles})


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
    if post.status == SocialPost.STATUS_PENDING:
        notify_review_needed(post)
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
        if not can_review_post(request.user, post):
            msg = ("You can't review your own post — another reviewer has to." if can_review(request.user)
                   else 'Only reviewers can approve or reject posts.')
            return Response({'detail': msg}, status=403)
        if post.status != SocialPost.STATUS_PENDING:
            return Response({'detail': 'This post is not waiting for approval.'}, status=400)
        post.approved_by, post.approved_at = request.user, timezone.now()
        post.review_note = (request.data.get('note') or '')[:1000]
        if action == 'reject':
            post.status = SocialPost.STATUS_REJECTED
            post.save()
            notify_reviewed(post, approved=False)
        else:
            now_due = not post.scheduled_at or post.scheduled_at <= timezone.now()
            post.status = SocialPost.STATUS_PUBLISHING if now_due else SocialPost.STATUS_SCHEDULED
            post.save()
            notify_reviewed(post, approved=True)
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
            notify_review_needed(post)
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


# ── Analytics ─────────────────────────────────────────────────────────────────

METRIC_KEYS = ['views', 'reach', 'impressions', 'likes', 'comments', 'shares', 'saves', 'quotes', 'clicks']


@api_view(['GET'])
@permission_classes([CanPost])
def analytics(request):
    """GET /api/social/analytics/?days=30 — totals per network, follower
    growth, best posts and each post's numbers."""
    from datetime import timedelta
    from .insights import supports
    from .models import SocialFollowerStat
    try:
        days = max(1, min(int(request.query_params.get('days', 30)), 365))
    except ValueError:
        days = 30
    since = timezone.now() - timedelta(days=days)
    targets = list(SocialPostTarget.objects.filter(status='published', published_at__gte=since)
                   .select_related('account', 'post', 'post__author'))
    per_net = {}
    for t in targets:
        n = per_net.setdefault(t.account_id, {'account_id': t.account_id, 'account': t.account.name,
                                               'platform': t.account.platform, 'posts': 0,
                                               **{k: 0 for k in METRIC_KEYS}})
        n['posts'] += 1
        for k in METRIC_KEYS:
            n[k] += int((t.metrics or {}).get(k) or 0)
    # Followers now vs. the start of the period
    for acc in SocialAccount.objects.filter(is_active=True):
        stats = list(SocialFollowerStat.objects.filter(account=acc).order_by('date').values('date', 'followers'))
        row = per_net.setdefault(acc.pk, {'account_id': acc.pk, 'account': acc.name, 'platform': acc.platform,
                                          'posts': 0, **{k: 0 for k in METRIC_KEYS}})
        now_f = stats[-1]['followers'] if stats else None
        before = next((s['followers'] for s in stats if s['date'] >= since.date()), None)
        row.update(followers=now_f, followers_change=(now_f - before) if now_f is not None and before is not None else None,
                   followers_series=[{'date': str(s['date']), 'value': s['followers']} for s in stats[-90:]],
                   supports={'numbers': supports(acc.platform, 'metrics'), 'comments':
                             supports(acc.platform, 'comments') or acc.platform == 'telegram'})

    def engagement(t):
        m = t.metrics or {}
        return sum(int(m.get(k) or 0) for k in ('likes', 'comments', 'shares', 'saves', 'quotes'))

    posts = {}
    for t in sorted(targets, key=lambda x: x.published_at, reverse=True):
        p = posts.setdefault(t.post_id, {'id': t.post_id, 'text': t.post.text[:200],
                                         'author': t.post.author.username if t.post.author_id else None,
                                         'published_at': _iso(t.post.published_at), 'networks': [], 'engagement': 0})
        p['networks'].append({'account': t.account.name, 'platform': t.account.platform, 'url': t.url,
                              'metrics': {k: v for k, v in (t.metrics or {}).items() if k in METRIC_KEYS},
                              'metrics_at': _iso(t.metrics_at), 'sync_error': t.sync_error})
        p['engagement'] += engagement(t)
    post_list = list(posts.values())
    last = max((t.metrics_at for t in targets if t.metrics_at), default=None)
    return Response({
        'days': days, 'last_synced': _iso(last),
        'networks': sorted(per_net.values(), key=lambda r: r['platform']),
        'totals': {k: sum(n[k] for n in per_net.values()) for k in METRIC_KEYS + ['posts']},
        'top_posts': sorted(post_list, key=lambda p: p['engagement'], reverse=True)[:5],
        'posts': post_list[:100],
    })


@api_view(['POST'])
@permission_classes([CanPost])
def sync_now(request):
    """POST /api/social/sync/ — refresh numbers and comments now (at most once
    every 2 minutes, to stay inside the networks' rate limits)."""
    from django.core.cache import cache
    if not cache.add('social:sync-lock', 1, timeout=120):
        return Response({'detail': 'Refreshed a moment ago — try again in a couple of minutes.'}, status=429)
    from .tasks import sync_social_insights
    try:
        sync_social_insights.delay()
    except Exception:
        import threading
        from .sync import sync_all

        def run():
            from django.db import connection
            try:
                sync_all()
            finally:
                connection.close()
        threading.Thread(target=run, daemon=True).start()
    return Response({'ok': True})


# ── Inbox ─────────────────────────────────────────────────────────────────────

def _comment(c):
    t = c.target
    return {
        'id': c.pk, 'platform': c.account.platform, 'account': c.account.name, 'account_id': c.account_id,
        'author': c.author_name, 'handle': c.author_handle, 'text': c.text, 'url': c.permalink,
        'posted_at': _iso(c.posted_at), 'handled': c.handled,
        'handled_by': c.handled_by.username if c.handled_by_id else None,
        'can_reply': supports_reply(c.account.platform),
        'post': {'id': t.post_id, 'text': t.post.text[:140], 'url': t.url} if t else None,
        'replies': [{'id': r.pk, 'author': r.author_name, 'text': r.text, 'is_ours': r.is_ours,
                     'sent_by': r.sent_by.username if r.sent_by_id else None, 'posted_at': _iso(r.posted_at)}
                    for r in c.replies.select_related('sent_by').order_by('posted_at')],
    }


def supports_reply(platform):
    from .insights import supports
    return supports(platform, 'reply')


@api_view(['GET'])
@permission_classes([CanPost])
def inbox(request):
    """GET /api/social/inbox/?status=open|handled|all&platform=&page="""
    from .models import SocialComment
    qs = (SocialComment.objects.filter(is_ours=False, parent__isnull=True)
          .select_related('account', 'target__post', 'handled_by').order_by('-posted_at'))
    status = request.query_params.get('status', 'open')
    if status == 'open':
        qs = qs.filter(handled=False)
    elif status == 'handled':
        qs = qs.filter(handled=True)
    if request.query_params.get('platform'):
        qs = qs.filter(account__platform=request.query_params['platform'])
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except ValueError:
        page = 1
    total = qs.count()
    return Response({'total': total, 'page': page, 'pages': (total + 24) // 25,
                     'open_count': SocialComment.objects.filter(is_ours=False, parent__isnull=True,
                                                                handled=False).count(),
                     'results': [_comment(c) for c in qs[(page - 1) * 25: page * 25]]})


@api_view(['POST'])
@permission_classes([CanPost])
def inbox_reply(request, pk):
    """POST /api/social/inbox/<id>/reply/ {text} — answers from the brand account."""
    from .insights import INSIGHTS
    from .models import SocialComment
    c = get_object_or_404(SocialComment.objects.select_related('account', 'target', 'parent'), pk=pk)
    text = (request.data.get('text') or '').strip()
    if not text:
        return Response({'detail': 'Write a reply first.'}, status=400)
    if not supports_reply(c.account.platform):
        return Response({'detail': f'{c.account.get_platform_display()} doesn\'t allow replying from outside its app.'},
                        status=400)
    try:
        ext_id, url = INSIGHTS[c.account.platform].reply(c.account, c, text)
    except Exception as e:
        return Response({'detail': f'The network refused the reply: {e}'}, status=502)
    SocialComment.objects.create(account=c.account, target=c.target, parent=c, external_id=str(ext_id) or f'local-{c.pk}-{timezone.now().timestamp()}',
                                 author_name=c.account.name, text=text, permalink=url or '', posted_at=timezone.now(),
                                 is_ours=True, sent_by=request.user, handled=True)
    c.handled, c.handled_by, c.handled_at = True, request.user, timezone.now()
    c.save(update_fields=['handled', 'handled_by', 'handled_at'])
    c.refresh_from_db()
    return Response(_comment(c))


@api_view(['POST'])
@permission_classes([CanPost])
def inbox_handled(request, pk):
    """POST /api/social/inbox/<id>/handled/ {handled: true|false}"""
    from .models import SocialComment
    c = get_object_or_404(SocialComment, pk=pk)
    c.handled = bool(request.data.get('handled', True))
    c.handled_by, c.handled_at = (request.user, timezone.now()) if c.handled else (None, None)
    c.save(update_fields=['handled', 'handled_by', 'handled_at'])
    return Response(_comment(c))
