from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def notify_followers_new_chapter(chapter_id: int):
    """Notify all followers of the story's author about a new chapter."""
    from apps.chapters.models import Chapter
    from apps.users.models import Follow
    from .models import Notification

    try:
        chapter = Chapter.objects.select_related('story__author').get(pk=chapter_id)
    except Chapter.DoesNotExist:
        return

    story   = chapter.story
    author  = story.author
    followers = Follow.objects.filter(following=author).select_related('follower')

    notifications = [
        Notification(
            recipient=follow.follower,
            notification_type=Notification.TYPE_NEW_CHAPTER,
            title=f'New chapter from {author.username}!',
            message=f'Chapter {chapter.chapter_number}: "{chapter.title}" is now available in "{story.title}".',
            data={'story_slug': story.slug, 'chapter_number': chapter.chapter_number},
        )
        for follow in followers
    ]
    Notification.objects.bulk_create(notifications, batch_size=500)

    # Push notification
    _send_push_bulk(
        [f.follower for f in followers],
        title=f'📖 New chapter: {story.title}',
        body=f'Chapter {chapter.chapter_number} — {chapter.title}',
        data={'story_slug': story.slug, 'chapter_number': str(chapter.chapter_number)},
    )


@shared_task
def notify_tip_received(tip_id: int):
    """Notify author that they received a tip."""
    from apps.tips.models import Tip
    from .models import Notification

    try:
        tip = Tip.objects.select_related('sender', 'recipient', 'story').get(pk=tip_id)
    except Tip.DoesNotExist:
        return

    Notification.objects.create(
        recipient=tip.recipient,
        notification_type=Notification.TYPE_TIP_RECEIVED,
        title='You received a tip! 🎉',
        message=f'{tip.sender.username} tipped you {tip.coins_amount} coins on "{tip.story.title}".'
                + (f' Message: {tip.message}' if tip.message else ''),
        data={'story_slug': tip.story.slug, 'coins': tip.coins_amount},
    )
    _send_push(
        tip.recipient,
        title='💰 New tip received!',
        body=f'{tip.sender.username} sent you {tip.coins_amount} coins.',
        data={'story_slug': tip.story.slug},
    )


@shared_task
def notify_new_follower(follower_id: int, following_id: int):
    from django.contrib.auth import get_user_model
    from .models import Notification

    User = get_user_model()
    try:
        follower  = User.objects.get(pk=follower_id)
        following = User.objects.get(pk=following_id)
    except User.DoesNotExist:
        return

    Notification.objects.create(
        recipient=following,
        notification_type=Notification.TYPE_NEW_FOLLOWER,
        title='New follower!',
        message=f'{follower.username} started following you.',
        data={'username': follower.username},
    )


@shared_task
def notify_comment_reply(comment_id: int):
    from apps.comments.models import Comment
    from .models import Notification

    try:
        comment = Comment.objects.select_related('user', 'parent__user', 'story').get(pk=comment_id)
    except Comment.DoesNotExist:
        return

    if not comment.parent:
        return

    parent_author = comment.parent.user
    if parent_author == comment.user:
        return

    Notification.objects.create(
        recipient=parent_author,
        notification_type=Notification.TYPE_COMMENT_REPLY,
        title='Someone replied to your comment!',
        message=f'{comment.user.username} replied: "{comment.content[:100]}"',
        data={'story_slug': comment.story.slug},
    )


def _send_push(user, title: str, body: str, data: dict = None):
    """Send FCM push notification to a single user."""
    from .models import DeviceToken
    tokens = DeviceToken.objects.filter(user=user, is_active=True).values_list('token', flat=True)
    if tokens:
        _fcm_send(list(tokens), title, body, data or {})


def _send_push_bulk(users, title: str, body: str, data: dict = None):
    """Send FCM push notifications to multiple users."""
    from .models import DeviceToken
    tokens = DeviceToken.objects.filter(
        user__in=users, is_active=True
    ).values_list('token', flat=True)
    if tokens:
        _fcm_send(list(tokens), title, body, data or {})


def _fcm_send(tokens: list, title: str, body: str, data: dict):
    """Send via Firebase Cloud Messaging (FCM v1 API)."""
    import requests
    from django.conf import settings

    fcm_key = getattr(settings, 'FCM_SERVER_KEY', '')
    if not fcm_key or not tokens:
        return

    headers = {
        'Authorization': f'key={fcm_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'registration_ids': tokens[:500],
        'notification': {'title': title, 'body': body},
        'data': data,
    }
    try:
        resp = requests.post(
            'https://fcm.googleapis.com/fcm/send',
            json=payload, headers=headers, timeout=10
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error(f'FCM push failed: {e}')
