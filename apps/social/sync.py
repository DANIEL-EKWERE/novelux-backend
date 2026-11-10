"""Pulling numbers and comments back from the networks (hourly, or on demand)."""
import logging
from datetime import timedelta

from django.utils import timezone

from .insights import INSIGHTS, NotSupported, supports
from .models import SocialAccount, SocialComment, SocialFollowerStat, SocialPostTarget

logger = logging.getLogger(__name__)
SYNC_DAYS = 30        # posts older than this stop being refreshed
MAX_TARGETS = 200


def _store_comments(acc, target, items):
    """Save new comments; link replies to their parent. Returns how many were new."""
    new = 0
    by_ext = {}
    for c in sorted(items, key=lambda x: (x.get('parent_id') is not None, x.get('at') or timezone.now())):
        parent = None
        if c.get('parent_id'):
            parent = by_ext.get(c['parent_id']) or SocialComment.objects.filter(
                account=acc, external_id=c['parent_id']).first()
        obj, created = SocialComment.objects.get_or_create(
            account=acc, external_id=str(c['id']),
            defaults={'target': target, 'parent': parent, 'author_name': (c.get('name') or '')[:200],
                      'author_handle': (c.get('handle') or '')[:200], 'text': c.get('text') or '',
                      'permalink': (c.get('url') or '')[:500], 'posted_at': c.get('at') or timezone.now(),
                      'is_ours': bool(c.get('ours')), 'handled': bool(c.get('ours'))})
        by_ext[str(c['id'])] = obj
        if created and not obj.is_ours:
            new += 1
            # Someone answered a comment from another app — no need to keep it open
        if created and obj.is_ours and parent and not parent.handled:
            parent.handled, parent.handled_at = True, timezone.now()
            parent.save(update_fields=['handled', 'handled_at'])
    return new


def sync_target(t):
    acc = t.account
    impl = INSIGHTS.get(acc.platform)
    errors = []
    if supports(acc.platform, 'metrics'):
        try:
            m = impl.metrics(acc, t)
            t.metrics = {**(t.metrics or {}), **m}
            t.metrics_at = timezone.now()
        except Exception as e:
            errors.append(f'Numbers: {e}')
    new = 0
    if supports(acc.platform, 'comments'):
        try:
            new = _store_comments(acc, t, impl.comments(acc, t))
        except Exception as e:
            errors.append(f'Comments: {e}')
    t.sync_error = '; '.join(errors)[:2000]
    t.save(update_fields=['metrics', 'metrics_at', 'sync_error', 'url'])
    return new


def sync_telegram(acc):
    """Telegram has no per-post comment API: read the bot's new messages and
    keep the ones replying to our channel posts."""
    from .insights import Telegram
    posts = {t.external_id: t for t in SocialPostTarget.objects.filter(account=acc, status='published')}
    items = []
    for m in Telegram.updates(acc):
        target = posts.get(m['channel_msg'])
        parent_ext = m['reply_to'] if not target else None
        if not target:
            parent = SocialComment.objects.filter(account=acc, external_id=m['reply_to']).first()
            if not parent:
                continue
            target = parent.target
        items.append(({**m, 'parent_id': parent_ext}, target))
    new = 0
    for m, target in items:
        new += _store_comments(acc, target, [m])
    return new


def sync_all(days=SYNC_DAYS, only_account=None):
    since = timezone.now() - timedelta(days=days)
    accounts = SocialAccount.objects.filter(is_active=True)
    if only_account:
        accounts = accounts.filter(pk=only_account)
    today = timezone.localdate()
    new_comments = 0
    for acc in accounts:
        impl = INSIGHTS.get(acc.platform)
        if supports(acc.platform, 'followers'):
            try:
                SocialFollowerStat.objects.update_or_create(account=acc, date=today,
                                                            defaults={'followers': impl.followers(acc)})
            except Exception as e:
                logger.info('Follower count failed for %s: %s', acc, e)
        if acc.platform == 'telegram' and supports('telegram', 'updates'):
            try:
                new_comments += sync_telegram(acc)
            except Exception as e:
                logger.info('Telegram comments failed: %s', e)
    targets = (SocialPostTarget.objects.filter(status='published', published_at__gte=since, account__in=accounts)
               .select_related('account').order_by('-published_at')[:MAX_TARGETS])
    for t in targets:
        new_comments += sync_target(t)
    return f'{len(targets)} post(s) refreshed, {new_comments} new comment(s)'


__all__ = ['sync_all', 'sync_target', 'NotSupported']
