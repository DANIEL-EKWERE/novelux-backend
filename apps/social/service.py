"""Who can post, and getting a post out to each network."""
import logging
import mimetypes

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import TEXT_LIMITS, SocialPost, SocialPostTarget, SocialSettings
from .publishers import PUBLISHERS, Media, PostContext, PublishError

logger = logging.getLogger(__name__)


def can_manage(user):
    """Connect accounts and change settings: owners/admins only."""
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == 'admin'))


def can_post(user):
    if can_manage(user):
        return True
    return bool(user and user.is_authenticated and user.role in (SocialSettings.get().poster_roles or []))


def can_review(user):
    """Approve / reject waiting posts: admins, and chief editors when that's
    switched on in Social settings."""
    if can_manage(user):
        return True
    return bool(user and user.is_authenticated and user.role == 'ce' and SocialSettings.get().ce_can_review)


def can_review_post(user, post):
    """Reviewers can't approve their own post (admins excepted)."""
    return can_review(user) and (can_manage(user) or post.author_id != user.pk)


def needs_approval(user):
    """With approval on, every SE/CE post waits for review — only admins post
    straight away."""
    return SocialSettings.get().require_approval and not can_manage(user)


def reviewers():
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    User = get_user_model()
    q = Q(is_superuser=True) | Q(role='admin')
    if SocialSettings.get().ce_can_review:
        q |= Q(role='ce')
    return User.objects.filter(q, is_active=True)


def _notify(user, title, message, post):
    try:
        from apps.notifications.services import create_notification
        create_notification(user, 'system', title, message,
                            data={'screen': 'social', 'post_id': post.pk, 'url': '/social/'}, send_push=False)
    except Exception:
        logger.exception('Social notification failed')


def notify_review_needed(post):
    who = post.author.username if post.author_id else 'Someone'
    for r in reviewers().exclude(pk=post.author_id):
        _notify(r, 'Social post waiting for review',
                f'{who} wants to post: "{post.text[:80]}". Review it in Social → Posts → Waiting approval.', post)


def notify_reviewed(post, approved):
    if not post.author_id:
        return
    by = post.approved_by.username if post.approved_by_id else 'A reviewer'
    if approved:
        _notify(post.author, 'Your social post was approved', f'{by} approved your post — it\'s going out now.', post)
    else:
        note = f' Note: {post.review_note}' if post.review_note else ''
        _notify(post.author, 'Your social post was not approved', f'{by} rejected your post.{note}', post)


def _absolute(url):
    if url.startswith('http'):
        return url
    base = getattr(settings, 'SITE_URL', '').rstrip('/')
    return f'{base}{url}'


def _media(m):
    def read(f=m.file):
        f.open('rb')
        try:
            return f.read()
        finally:
            f.close()
    ctype = mimetypes.guess_type(m.file.name)[0] or ('video/mp4' if m.kind == 'video' else 'image/jpeg')
    return Media(_absolute(m.file.url), read, name=m.file.name.rsplit('/', 1)[-1], content_type=ctype)


def context_for(post, target):
    media = list(post.media.all())
    videos = [_media(m) for m in media if m.kind == 'video']
    images = [_media(m) for m in media if m.kind == 'image']
    return PostContext(text=target.text or post.text, link=post.link, title=post.title,
                       images=[] if videos else images, video=videos[0] if videos else None)


def check_lengths(post):
    """Problems to fix before posting: [(account name, message)]."""
    problems = []
    for t in post.targets.select_related('account'):
        limit = TEXT_LIMITS.get(t.account.platform)
        text = (t.text or post.text) + (('\n\n' + post.link) if post.link and post.link not in (t.text or post.text) else '')
        if limit and len(text) > limit:
            problems.append((t.account.name, f'{len(text)}/{limit} characters'))
    return problems


def publish_post(post_id):
    """Post to every account that hasn't succeeded yet. Safe to call again
    (retries only the failed ones)."""
    with transaction.atomic():
        post = SocialPost.objects.select_for_update().get(pk=post_id)
        if post.status not in (SocialPost.STATUS_SCHEDULED, SocialPost.STATUS_PUBLISHING,
                               SocialPost.STATUS_FAILED, SocialPost.STATUS_PARTIAL, SocialPost.STATUS_DRAFT):
            return post
        post.status = SocialPost.STATUS_PUBLISHING
        post.save(update_fields=['status'])

    targets = post.targets.select_related('account').exclude(status=SocialPostTarget.STATUS_OK)
    for t in targets:
        acc = t.account
        t.attempts += 1
        if not acc.is_active:
            t.status, t.error = SocialPostTarget.STATUS_SKIPPED, 'Account is switched off.'
        else:
            try:
                ext_id, url = PUBLISHERS[acc.platform].publish(acc, context_for(post, t))
                t.status, t.external_id, t.url, t.error = SocialPostTarget.STATUS_OK, str(ext_id), url or '', ''
                t.published_at = timezone.now()
            except PublishError as e:
                t.status, t.error = SocialPostTarget.STATUS_FAILED, str(e)[:2000]
            except Exception as e:  # network down, bad credentials format, …
                logger.exception('Social publish failed (%s)', acc)
                t.status, t.error = SocialPostTarget.STATUS_FAILED, f'{type(e).__name__}: {e}'[:2000]
        t.save()

    results = list(post.targets.values_list('status', flat=True))
    ok = results.count(SocialPostTarget.STATUS_OK)
    post.status = (SocialPost.STATUS_PUBLISHED if ok == len(results) else
                   SocialPost.STATUS_PARTIAL if ok else SocialPost.STATUS_FAILED)
    if ok and not post.published_at:
        post.published_at = timezone.now()
    post.save(update_fields=['status', 'published_at'])
    return post


def publish_in_background(post_id):
    from .tasks import publish_social_post
    try:
        publish_social_post.delay(post_id)
    except Exception:
        # No broker and inline mode off — publish in a thread rather than not at all
        import threading

        def run():
            from django.db import connection
            try:
                publish_post(post_id)
            finally:
                connection.close()
        threading.Thread(target=run, daemon=True).start()


def publish_due():
    """Scheduled posts whose time has come (called by the scheduled-jobs runner)."""
    due = list(SocialPost.objects.filter(status=SocialPost.STATUS_SCHEDULED, scheduled_at__lte=timezone.now())
               .values_list('pk', flat=True)[:20])
    for pk in due:
        publish_post(pk)
    return f'{len(due)} scheduled post(s) sent'
