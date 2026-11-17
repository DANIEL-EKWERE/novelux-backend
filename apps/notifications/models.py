from django.db import models
from django.utils import timezone
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



class ReadingReminderSettings(models.Model):
    """Singleton: the "continue reading" push sent when a reader stops mid-book.
    Edit the wording or timing in the Django admin."""
    enabled          = models.BooleanField(default=True)
    delay_minutes    = models.PositiveIntegerField(default=30,
                           help_text='Minutes after the last chapter was opened.')
    quiet_start_hour = models.PositiveSmallIntegerField(default=22,
                           help_text="Reader's local time (0–23). No reminders from this hour…")
    quiet_end_hour   = models.PositiveSmallIntegerField(default=8,
                           help_text='…until this hour; waiting reminders go out then.')
    title            = models.CharField(max_length=120, default='📖 {story}')
    body             = models.CharField(
                           max_length=255,
                           default='Chapter {chapter} is waiting — find out what happens next 👀',
                           help_text='You can use {story}, {chapter} (the next chapter) and {name}.')
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reading_reminder_settings'
        verbose_name = verbose_name_plural = 'Continue-reading reminder settings'

    def __str__(self):
        return 'Continue-reading reminder settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ReadingReminder(models.Model):
    """The last chapter each reader opened, and whether we've sent the
    "continue reading" push for it (one per reading stop, at most one a day)."""
    user           = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                         related_name='reading_reminder')
    story          = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='+')
    chapter_number = models.PositiveIntegerField()
    last_read_at   = models.DateTimeField(db_index=True)
    handled_read_at = models.DateTimeField(null=True, blank=True,
                         help_text='The reading stop the latest reminder (or skip) was for.')
    sent_at        = models.DateTimeField(null=True, blank=True, db_index=True)
    sent_count     = models.PositiveIntegerField(default=0)
    returned_count = models.PositiveIntegerField(default=0,
                         help_text='Reminders followed by the reader coming back within 24 hours.')

    class Meta:
        db_table = 'reading_reminders'

    def __str__(self):
        return f'{self.user} — {self.story_id} ch.{self.chapter_number}'


class EngagementPushSettings(models.Model):
    """Singleton: scheduled pushes for check-in streaks, tasks / ad rewards and
    VIP. A reader gets at most one of these a day, at their local time."""
    checkin_enabled  = models.BooleanField(default=True, help_text='"Don\'t lose your streak" reminders.')
    checkin_hour     = models.PositiveSmallIntegerField(default=19, help_text="Reader's local hour (0–23).")
    rewards_enabled  = models.BooleanField(default=True, help_text='Tasks and ad-reward reminders.')
    rewards_hour     = models.PositiveSmallIntegerField(default=12)
    rewards_every_days = models.PositiveSmallIntegerField(default=3)
    vip_enabled      = models.BooleanField(default=True, help_text='"Tired of ads? Go VIP" to non-VIP readers.')
    vip_hour         = models.PositiveSmallIntegerField(default=20)
    vip_every_days   = models.PositiveSmallIntegerField(default=7)
    active_days      = models.PositiveSmallIntegerField(
                           default=14, help_text='Only readers who opened the app in this many days.')
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_push_settings'
        verbose_name = verbose_name_plural = 'Check-in / rewards / VIP push settings'

    def __str__(self):
        return 'Check-in / rewards / VIP push settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class EngagementPush(models.Model):
    """One scheduled push sent to one reader (for the daily limit and stats)."""
    KINDS = [('checkin', 'Check-in streak'), ('tasks', 'Tasks'), ('ads', 'Ad rewards'), ('vip', 'Go VIP')]
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='engagement_pushes')
    kind    = models.CharField(max_length=10, choices=KINDS, db_index=True)
    title   = models.CharField(max_length=150)
    body    = models.CharField(max_length=255)
    sent_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'engagement_pushes'
        ordering = ['-sent_at']
        indexes = [models.Index(fields=['user', 'sent_at'])]

    def __str__(self):
        return f'{self.user} — {self.kind} — {self.sent_at:%Y-%m-%d %H:%M}'
