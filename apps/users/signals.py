from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
 
User = get_user_model()
 
@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        from apps.notifications.services import on_user_signup
        # Delay slightly to let device token register first
        from django.utils import timezone
        import threading
        def _send():
            import time; time.sleep(5)
            on_user_signup(instance)
        threading.Thread(target=_send, daemon=True).start()