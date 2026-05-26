from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Chapter
 
@receiver(post_save, sender=Chapter)
def on_chapter_published(sender, instance, created, **kwargs):
    if created and instance.is_published:
        from apps.notifications.services import on_new_chapter
        on_new_chapter(instance.story, instance.title)