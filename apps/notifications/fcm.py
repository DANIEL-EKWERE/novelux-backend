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
            priority='high',
            notification=messaging.AndroidNotification(
                icon='ic_notification',
                color='#C15F3C',
                sound='default',
                channel_id='novelux_push',
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default', badge=1),
            ),
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
    )
    try:
        messaging.send(message)
        return True
    except Exception as e:
        logger.error(f'FCM topic send failed: {e}')
        return False