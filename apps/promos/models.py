"""Book promotions shown when the app opens.

Two styles:
  • splash — a full-screen poster with a "Skip" countdown and "View more";
  • popup  — a card over the home screen: artwork, the book cover, a tagline,
             "View more" and a close button.
Each promotion is shown once per reader, and at most one per app launch.
Admins, chief editors and senior editors create them at /promotions/.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


def _promo_path(instance, filename):
    return f'promos/{timezone.now():%Y/%m}/{filename}'


class InAppPromo(models.Model):
    KIND_SPLASH, KIND_POPUP = 'splash', 'popup'
    KINDS = [(KIND_SPLASH, 'Full screen (on open)'), (KIND_POPUP, 'Pop-up card')]

    kind         = models.CharField(max_length=10, choices=KINDS, default=KIND_POPUP)
    story        = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='in_app_promos')
    name         = models.CharField(max_length=120, blank=True, help_text='For the team only.')
    image        = models.ImageField(upload_to=_promo_path, blank=True,
                                     help_text='Full screen: the poster (tall, about 9:16). '
                                               'Pop-up: background artwork (optional — the cover is used otherwise).')
    tagline      = models.CharField(max_length=140, blank=True, help_text='Pop-up text, e.g. a hook line.')
    button_text  = models.CharField(max_length=30, default='View more')
    skip_seconds = models.PositiveSmallIntegerField(default=3, help_text='Full screen: countdown before it closes.')
    starts_at    = models.DateTimeField(default=timezone.now)
    ends_at      = models.DateTimeField(null=True, blank=True)
    is_active    = models.BooleanField(default=True)
    priority     = models.SmallIntegerField(default=0, help_text='Higher shows first.')
    created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='+')
    created_at   = models.DateTimeField(auto_now_add=True)
    impressions  = models.PositiveIntegerField(default=0)
    clicks       = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'in_app_promos'
        ordering = ['-priority', '-starts_at']

    def __str__(self):
        return f'{self.get_kind_display()} — {self.story}'

    def is_live(self, now=None):
        now = now or timezone.now()
        return self.is_active and self.starts_at <= now and (self.ends_at is None or self.ends_at > now)


class PromoView(models.Model):
    """A signed-in reader saw a promotion (so it isn't shown to them again)."""
    promo      = models.ForeignKey(InAppPromo, on_delete=models.CASCADE, related_name='views')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    seen_at    = models.DateTimeField(auto_now_add=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'in_app_promo_views'
        unique_together = ('promo', 'user')
