"""Posting to HuxNovel's social accounts from one dashboard.

Credentials (access tokens, bot tokens, API keys) are stored encrypted with a
key derived from SECRET_KEY and are never sent back to the browser.
"""
import base64
import hashlib
import json

from django.conf import settings
from django.db import models

PLATFORMS = [
    ('facebook',  'Facebook Page'),
    ('instagram', 'Instagram'),
    ('threads',   'Threads'),
    ('x',         'X (Twitter)'),
    ('tiktok',    'TikTok'),
    ('linkedin',  'LinkedIn Page'),
    ('youtube',   'YouTube'),
    ('telegram',  'Telegram channel'),
]

# Caption / text length limits per network
TEXT_LIMITS = {
    'facebook': 63206, 'instagram': 2200, 'threads': 500, 'x': 280, 'tiktok': 2200,
    'linkedin': 3000, 'youtube': 5000, 'telegram': 4096,
}


def _fernet():
    from cryptography.fernet import Fernet
    key = hashlib.sha256(('social-credentials:' + settings.SECRET_KEY).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


class SocialAccount(models.Model):
    """One connected account (a Facebook Page, an Instagram account, a Telegram
    channel…). `config` holds non-secret ids; secrets live in `_secrets`."""
    platform     = models.CharField(max_length=20, choices=PLATFORMS)
    name         = models.CharField(max_length=120, help_text='Shown in the dashboard, e.g. "HuxNovel Facebook"')
    handle       = models.CharField(max_length=120, blank=True)
    config       = models.JSONField(default=dict, blank=True)
    _secrets     = models.TextField(blank=True, db_column='secrets')
    is_active    = models.BooleanField(default=True)
    connected_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='+')
    connected_at = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    last_error   = models.TextField(blank=True)

    class Meta:
        db_table = 'social_accounts'
        ordering = ['platform', 'name']

    def __str__(self):
        return f'{self.get_platform_display()} — {self.name}'

    @property
    def secrets(self):
        if not self._secrets:
            return {}
        try:
            return json.loads(_fernet().decrypt(self._secrets.encode()).decode())
        except Exception:
            return {}

    @secrets.setter
    def secrets(self, value):
        self._secrets = _fernet().encrypt(json.dumps(value or {}).encode()).decode()

    def update_secrets(self, **changes):
        s = self.secrets
        s.update({k: v for k, v in changes.items() if v is not None})
        self.secrets = s


class SocialSettings(models.Model):
    """Singleton. Approval is off by default — team posts go out directly."""
    require_approval = models.BooleanField(
        default=False, help_text='When on, posts by editors wait for an admin to approve them.')
    poster_roles     = models.JSONField(
        default=list, blank=True,
        help_text='Roles allowed to post (admins always can). Default: senior and chief editors.')
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'social_settings'
        verbose_name_plural = 'Social settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'poster_roles': ['se', 'ce']})
        return obj


class SocialPost(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PENDING = 'pending_approval'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_PUBLISHING = 'publishing'
    STATUS_PUBLISHED = 'published'
    STATUS_PARTIAL = 'partial'
    STATUS_FAILED = 'failed'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [(s, s.replace('_', ' ').title()) for s in [
        STATUS_DRAFT, STATUS_PENDING, STATUS_SCHEDULED, STATUS_PUBLISHING, STATUS_PUBLISHED,
        STATUS_PARTIAL, STATUS_FAILED, STATUS_REJECTED]]

    author       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                     related_name='social_posts')
    text         = models.TextField(blank=True)
    link         = models.URLField(blank=True)
    title        = models.CharField(max_length=100, blank=True, help_text='Used by YouTube (video title).')
    story        = models.ForeignKey('stories.Story', null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='social_posts', help_text='Book being promoted, if any.')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    approved_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='+')
    approved_at  = models.DateTimeField(null=True, blank=True)
    review_note  = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'social_posts'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d} — {self.text[:40]}'


def _media_path(instance, filename):
    return f'social/{instance.post_id or "new"}/{filename}'


class SocialMedia(models.Model):
    post       = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='media')
    file       = models.FileField(upload_to=_media_path)
    kind       = models.CharField(max_length=10, choices=[('image', 'Image'), ('video', 'Video')])
    order      = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'social_media'
        ordering = ['order', 'pk']


class SocialPostTarget(models.Model):
    """One post going to one account — each has its own result."""
    STATUS_WAITING, STATUS_OK, STATUS_FAILED, STATUS_SKIPPED = 'waiting', 'published', 'failed', 'skipped'
    post        = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='targets')
    account     = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name='targets')
    text        = models.TextField(blank=True, help_text='Text just for this network (blank = the main text).')
    status      = models.CharField(max_length=10, default=STATUS_WAITING)
    external_id = models.CharField(max_length=200, blank=True)
    url         = models.URLField(blank=True, max_length=500)
    error       = models.TextField(blank=True)
    attempts    = models.PositiveSmallIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'social_post_targets'
        unique_together = ('post', 'account')
