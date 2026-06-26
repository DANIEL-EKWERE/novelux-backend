import threading
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        from apps.notifications.services import on_user_signup
        def _send():
            import time; time.sleep(5)
            on_user_signup(instance)
        threading.Thread(target=_send, daemon=True).start()


@receiver(post_save, sender='users.AuthorKYC')
def on_kyc_submitted(sender, instance, created, **kwargs):
    """
    Trigger OCR processing whenever a KYC record is first created
    OR when id_front/id_back images are updated on a pending record.
    Uses Celery if available; falls back to a background thread.
    """
    from apps.users.models import AuthorKYC

    should_process = created or (
        instance.status == AuthorKYC.STATUS_PENDING
        and (instance.id_front or instance.id_document)
    )
    if not should_process:
        return

    kyc_id = instance.pk

    def _run_in_thread():
        from apps.users.tasks import _run_ocr_and_match
        try:
            _run_ocr_and_match(kyc_id)
        except Exception as exc:
            logger.error('KYC signal fallback OCR failed kyc_id=%s: %s', kyc_id, exc)

    try:
        from apps.users.tasks import process_kyc_ocr
        process_kyc_ocr.delay(kyc_id)
    except Exception:
        # Celery not reachable — run synchronously in a background thread
        threading.Thread(target=_run_in_thread, daemon=True).start()