"""
Editorial Signals
=================
1. When a User with role=se is saved → auto-generate editor_code
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='users.User')
def generate_se_editor_code(sender, instance, created, **kwargs):
    """
    As soon as an SE account is saved (created OR role changed to se),
    ensure they have an editor_code so they can invite authors.
    """
    if instance.role != 'se':
        return
    if instance.editor_code:
        return
    instance.generate_editor_code()
