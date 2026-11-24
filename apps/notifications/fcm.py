import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import logging
 
logger = logging.getLogger(__name__)
 
_app = None
 
def _get_app():
    global _app
    if _app is None:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        _app = firebase_admin.initialize_app(cred)
    return _app
 
 
def send_to_tokens(tokens: list, title: str, body: str,
                   data: dict = None, image_url: str = '') -> dict:
    # \"\"\"
    # Send a multicast notification to up to 500 tokens at once.
    #Returns {'success': N, 'failed': N}.
    # \"\"\"
    _get_app()
    if not tokens:
        return {'success': 0, 'failed': 0}
 
    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(
            title=title,
            body=body,
            image=image_url or None,
        ),
        data={str(k): str(v) for k, v in (data or {}).items()},
        android=messaging.AndroidConfig(
            priority='high',                    # delivery priority — wakes device
            notification=messaging.AndroidNotification(
                icon='ic_notification',
                color='#C15F3C',
                sound='default',
                channel_id='high_importance_channel',
                #notification_priority='PRIORITY_HIGH',  # display priority — shows heads-up popup
                visibility='public',
                default_vibrate_timings=True,
            ),
        ),
        apns=messaging.APNSConfig(
            headers={'apns-priority': '10'},    # 10 = immediate delivery
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(title=title, body=body),  # required for banner
                    sound='default',
                    badge=1,
                    # Lets an iOS notification service extension attach the
                    # image; without one, iOS simply shows the text.
                    mutable_content=bool(image_url),
                ),
            ),
            fcm_options=messaging.APNSFCMOptions(image=image_url) if image_url else None,
        ),
    )

    try:
        response = messaging.send_each_for_multicast(message)
        return {
            'success': response.success_count,
            'failed':  response.failure_count,
        }
    except Exception as e:
        logger.error(f'FCM multicast failed: {e}')
        return {'success': 0, 'failed': len(tokens)}
 
 
def send_to_topic(topic: str, title: str, body: str,
                  data: dict = None) -> bool:
    # \"\"\"Send to an FCM topic (e.g. 'all_users').\"\"\"
    _get_app()
    message = messaging.Message(
        topic=topic,
        notification=messaging.Notification(title=title, body=body),
        data={str(k): str(v) for k, v in (data or {}).items()},
        android=messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='high_importance_channel',
                # notification_priority='PRIORITY_HIGH',
                visibility='public',
                default_vibrate_timings=True,
            ),
        ),
        apns=messaging.APNSConfig(
            headers={'apns-priority': '10'},
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(title=title, body=body),
                    sound='default',
                    badge=1,
                ),
            ),
        ),
    )
    try:
        messaging.send(message)
        return True
    except Exception as e:
        logger.error(f'FCM topic send failed: {e}')
        return False

def send_personal(items):
    """Send a different message to each device in one go (500 per batch).
    items: [(token, title, body, data)]. Returns (sent, failed, dead_tokens)."""
    if not items:
        return 0, 0, []
    _get_app()
    sent = failed = 0
    dead = []
    for i in range(0, len(items), 500):
        chunk = items[i:i + 500]
        msgs = [messaging.Message(
            token=tok,
            notification=messaging.Notification(title=title, body=body),
            data={str(k): str(v) for k, v in (data or {}).items()},
            android=messaging.AndroidConfig(priority='high', notification=messaging.AndroidNotification(
                icon='ic_notification', color='#C15F3C', sound='default', channel_id='high_importance_channel')),
            apns=messaging.APNSConfig(headers={'apns-priority': '10'}, payload=messaging.APNSPayload(
                aps=messaging.Aps(alert=messaging.ApsAlert(title=title, body=body), sound='default'))),
        ) for tok, title, body, data in chunk]
        try:
            res = messaging.send_each(msgs)
        except Exception as e:
            logger.error(f'FCM personal batch failed: {e}')
            failed += len(chunk)
            continue
        for (tok, *_), r in zip(chunk, res.responses):
            if r.success:
                sent += 1
            else:
                failed += 1
                if r.exception and type(r.exception).__name__ in ('UnregisteredError', 'SenderIdMismatchError'):
                    dead.append(tok)
    return sent, failed, dead
