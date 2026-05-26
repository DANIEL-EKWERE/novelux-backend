from apps.users.models import FCMDevice
from .models import DeviceToken, Notification
from .fcm    import send_to_tokens, send_to_topic
import logging

logger = logging.getLogger(__name__)

CHUNK = 500  # FCM max per multicast call


# ── Core helper — always call this instead of notify_user directly ─────────────
def create_notification(user, notification_type: str, title: str, message: str,
                        data: dict = None, send_push: bool = True, image_url: str = ''):
    """
    Create a Notification DB record (shows in the in-app bell) AND
    optionally send an FCM push to the user's devices.

    This is the single point of truth for all in-app notifications.
    """
    # 1. Persist to DB
    try:
        Notification.objects.create(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
        )
    except Exception as e:
        logger.error('create_notification: DB save failed for %s: %s', user.username, e)

    # 2. FCM push
    if send_push:
        notify_user(user, title=title, body=message, data=data, image_url=image_url)


# ── Low-level push-only (kept for internal use) ────────────────────────────────
def notify_user(user, title: str, body: str,
                data: dict = None, image_url: str = ''):
    """Send FCM push only — does NOT create a DB record. Use create_notification instead."""
    tokens = list(
        FCMDevice
            .filter(user=user, is_active=True)
            .values_list('token', flat=True)
    )
    if not tokens:
        return
    send_to_tokens(tokens, title, body, data, image_url)


def notify_all(title: str, body: str, data: dict = None, image_url: str = ''):
    """Send FCM push to every active token in chunks of 500."""
    total_ok = 0
    total_fail = 0
    qs = FCMDevice.objects.filter(is_active=True).values_list('token', flat=True)
    tokens = list(qs)
    for i in range(0, len(tokens), CHUNK):
        chunk = tokens[i:i + CHUNK]
        r = send_to_tokens(chunk, title, body, data, image_url)
        total_ok   += r['success']
        total_fail += r['failed']
    return {'success': total_ok, 'failed': total_fail}


def notify_by_genre(genre_slug: str, title: str, body: str, data: dict = None):
    """Send FCM push to users who have that genre in their preferences."""
    from apps.users.models import UserPreferences
    user_ids = UserPreferences.objects.filter(
        preferred_genres__contains=[genre_slug]
    ).values_list('user_id', flat=True)
    tokens = list(
        FCMDevice.objects
            .filter(user_id__in=user_ids, is_active=True)
            .values_list('token', flat=True)
    )
    if tokens:
        send_to_tokens(tokens, title, body, data)


# ── Event helpers — call these from views/signals/tasks ───────────────────────

def on_contract_threshold_reached(author, story):
    """Author's story hits the chapter threshold — prompt to apply."""
    create_notification(
        user=author,
        notification_type=Notification.TYPE_SYSTEM,
        title='Your story is ready for a contract! 🎉',
        message=f'"{story.title}" has reached the chapter threshold. Go to My Books and tap "Apply for Contract" to proceed.',
        data={'screen': 'my_books', 'slug': story.slug, 'action': 'apply_contract'},
    )


def on_contract_applied(author, story):
    """Author submitted a contract application."""
    create_notification(
        user=author,
        notification_type=Notification.TYPE_SYSTEM,
        title='Contract application submitted! 📋',
        message=f'Your application for "{story.title}" has been received and is now under review by your editor.',
        data={'screen': 'my_books', 'slug': story.slug},
    )


def on_se_approved(author, story):
    """SE approved the story — passed to CE."""
    create_notification(
        user=author,
        notification_type=Notification.TYPE_SYSTEM,
        title='Your story has been approved! 🎉',
        message=f'"{story.title}" has been approved by your Senior Editor and forwarded to the Chief Editor.',
        data={'screen': 'my_books', 'slug': story.slug},
    )


def on_se_revision_requested(author, story, note: str = ''):
    """SE sent the story back for revision."""
    create_notification(
        user=author,
        notification_type=Notification.TYPE_SYSTEM,
        title='Revision requested for your story',
        message=f'Your editor has requested revisions on "{story.title}".'
                + (f' Note: {note}' if note else '') + ' Please update and resubmit.',
        data={'screen': 'my_books', 'slug': story.slug, 'action': 'revise'},
    )


def on_contract_sent(author, story, contract_type: str = 'non_exclusive'):
    """CE sent the contract to the author."""
    label = 'Exclusive' if contract_type == 'exclusive' else 'Non-Exclusive'
    create_notification(
        user=author,
        notification_type=Notification.TYPE_SYSTEM,
        title='Contract ready to sign! 📝',
        message=f'A {label} contract for "{story.title}" has been sent to your email. Open Novelux to review and sign.',
        data={'screen': 'my_books', 'slug': story.slug, 'action': 'sign_contract'},
    )


def on_contract_signed(author, story, published_count: int = 0):
    """Author accepted the contract."""
    create_notification(
        user=author,
        notification_type=Notification.TYPE_SYSTEM,
        title='Contract signed — you\'re live! 🚀',
        message=f'Welcome to the Novelux author programme! "{story.title}" is now live'
                + (f' with {published_count} chapter(s) published.' if published_count else '.'),
        data={'screen': 'my_books', 'slug': story.slug},
    )


def on_contract_rejected(author, story, reason: str = ''):
    """CE rejected the contract application."""
    create_notification(
        user=author,
        notification_type=Notification.TYPE_SYSTEM,
        title='Contract not approved',
        message=f'"{story.title}" was not approved for a contract at this time.'
                + (f' Reason: {reason}' if reason else ''),
        data={'screen': 'my_books', 'slug': story.slug},
    )


def on_user_signup(user):
    """Welcome notification after registration."""
    create_notification(
        user=user,
        notification_type=Notification.TYPE_SYSTEM,
        title='Welcome to NoveluX! 🎉',
        message='Your reading journey starts now. Earn 100 free coins just for signing up!',
        data={'screen': 'rewards'},
    )


def on_chapter_unlocked(user, story_title: str, chapter_num: int):
    create_notification(
        user=user,
        notification_type=Notification.TYPE_SYSTEM,
        title=f'Chapter {chapter_num} unlocked!',
        message=f'Continue reading {story_title}',
        data={'screen': 'story', 'action': 'read'},
    )


def on_tip_received(author, tipper_name: str, gift_label: str, story_title: str):
    """Notify an author when they receive a gift."""
    create_notification(
        user=author,
        notification_type=Notification.TYPE_TIP_RECEIVED,
        title=f'{tipper_name} sent you a {gift_label}! 🎁',
        message=f'For your story: {story_title}',
        data={'screen': 'earnings'},
    )


def on_new_chapter(story, chapter_title: str):
    """Notify everyone who bookmarked this story."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    bookmarker_ids = story.bookmarks.values_list('user_id', flat=True)
    notifications = [
        Notification(
            recipient_id=uid,
            notification_type=Notification.TYPE_NEW_CHAPTER,
            title=f'New chapter: {story.title}',
            message=chapter_title,
            data={'screen': 'story', 'slug': story.slug},
        )
        for uid in bookmarker_ids
    ]
    if notifications:
        Notification.objects.bulk_create(notifications, batch_size=500)
    # Push separately
    tokens = list(
        FCMDevice.objects
            .filter(user_id__in=bookmarker_ids, is_active=True)
            .values_list('token', flat=True)
    )
    if tokens:
        send_to_tokens(tokens,
            title=f'📖 New chapter: {story.title}',
            body=chapter_title,
            data={'screen': 'story', 'slug': story.slug},
        )


def on_daily_reward_available():
    """Broadcast daily check-in reminder (push only — no per-user DB record)."""
    notify_all(
        title='📚 Daily reward available!',
        body='Log in now to collect your coins and keep your streak alive.',
        data={'screen': 'rewards'})


def on_contest_deadline(hours_left: int):
    notify_all(
        title=f'⏰ Contest ends in {hours_left} hours!',
        body='Submit your story before time runs out.',
        data={'screen': 'contest'})