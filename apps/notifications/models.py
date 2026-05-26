from django.db import models
from django.contrib.auth import get_user_model

from config import settings

User = get_user_model()


class Notification(models.Model):
    TYPE_NEW_CHAPTER    = 'new_chapter'
    TYPE_TIP_RECEIVED   = 'tip_received'
    TYPE_NEW_FOLLOWER   = 'new_follower'
    TYPE_COMMENT_REPLY  = 'comment_reply'
    TYPE_COMMENT_LIKE   = 'comment_like'
    TYPE_VOTE_RESULT    = 'vote_result'
    TYPE_BONUS_EARNED   = 'bonus_earned'
    TYPE_SYSTEM         = 'system'

    TYPE_CHOICES = [
        (TYPE_NEW_CHAPTER,   'New Chapter'),
        (TYPE_TIP_RECEIVED,  'Tip Received'),
        (TYPE_NEW_FOLLOWER,  'New Follower'),
        (TYPE_COMMENT_REPLY, 'Comment Reply'),
        (TYPE_COMMENT_LIKE,  'Comment Like'),
        (TYPE_VOTE_RESULT,   'Vote Result'),
        (TYPE_BONUS_EARNED,  'Bonus Earned'),
        (TYPE_SYSTEM,        'System'),
    ]

    recipient     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title         = models.CharField(max_length=255)
    message       = models.TextField()
    data          = models.JSONField(default=dict, blank=True)
    is_read       = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.notification_type}] → {self.recipient.username}: {self.title}'


# class DeviceToken(models.Model):
#     """FCM push notification device tokens."""
#     PLATFORM_ANDROID = 'android'
#     PLATFORM_IOS     = 'ios'
#     PLATFORM_CHOICES = [
#         (PLATFORM_ANDROID, 'Android'),
#         (PLATFORM_IOS,     'iOS'),
#     ]

#     user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
#     token      = models.CharField(max_length=500, unique=True)
#     platform   = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
#     is_active  = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'device_tokens'

#     def __str__(self):
#         return f'{self.user.username} [{self.platform}]'


class DeviceToken(models.Model):
    # \"\"\"One row per device. Updated on every app launch.\"\"\"
    PLATFORM_CHOICES = [('Android', 'Android'), ('iOS', 'iOS')]
 
    user         = models.ForeignKey(settings.AUTH_USER_MODEL,
                       on_delete=models.CASCADE,
                       related_name='device_tokens',
                       null=True, blank=True)
    token        = models.CharField(max_length=512, unique=True)
    platform     = models.CharField(max_length=10, choices=PLATFORM_CHOICES,
                       default='Android')
    device_model = models.CharField(max_length=200, blank=True, default='')
    app_version  = models.CharField(max_length=50,  blank=True, default='')
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
 
    class Meta:
        ordering = ['-updated_at']
 
    def __str__(self):
        return f'{self.user} — {self.platform} — {self.token[:20]}...'
 
 
class PushNotificationLog(models.Model):
    # \"\"\"Audit log of every notification sent from admin panel.\"\"\"
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('sent',     'Sent'),
        ('failed',   'Failed'),
        ('partial',  'Partially sent'),
    ]
    AUDIENCE_CHOICES = [
        ('all',      'All users'),
        ('user',     'Specific user'),
        ('platform', 'By platform (Android/iOS)'),
        ('genre',    'By genre preference'),
    ]
 
    title       = models.CharField(max_length=200)
    body        = models.TextField()
    data        = models.JSONField(default=dict, blank=True,
                      help_text='Extra payload: {"screen": "story", "slug": "..."}')
    image_url   = models.URLField(blank=True, default='')
    audience    = models.CharField(max_length=20, choices=AUDIENCE_CHOICES,
                      default='all')
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL,
                      null=True, blank=True, on_delete=models.SET_NULL,
                      related_name='received_push_logs')
    platform    = models.CharField(max_length=10, blank=True, default='',
                      help_text='Android or iOS — leave blank for all')
    genre_slug  = models.CharField(max_length=100, blank=True, default='',
                      help_text='Filter by preferred genre if audience=genre')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES,
                      default='pending')
    sent_count  = models.IntegerField(default=0)
    failed_count= models.IntegerField(default=0)
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL,
                      null=True, blank=True, on_delete=models.SET_NULL,
                      related_name='sent_push_logs')
    created_at  = models.DateTimeField(auto_now_add=True)
    sent_at     = models.DateTimeField(null=True, blank=True)
 
    class Meta:
        ordering = ['-created_at']
 
    def __str__(self):
        return f'{self.title} — {self.status} — {self.created_at:%Y-%m-%d %H:%M}'

