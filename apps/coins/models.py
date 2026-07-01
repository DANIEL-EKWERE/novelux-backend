from django.db import models
from django.contrib.auth import get_user_model

from config import settings

User = get_user_model()


class CoinPackage(models.Model):
    package_id  = models.CharField(max_length=50, unique=True)
    label       = models.CharField(max_length=100)
    coins       = models.PositiveIntegerField()
    price_usd   = models.DecimalField(max_digits=8, decimal_places=2)
    bonus_coins = models.PositiveIntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coin_packages'
        ordering = ['price_usd']

    def __str__(self):
        return f'{self.label} ({self.coins} coins)'

    @property
    def total_coins(self):
        return self.coins + self.bonus_coins


class SubscriptionPlan(models.Model):
    plan_id            = models.CharField(max_length=50, unique=True)
    label              = models.CharField(max_length=100)
    price_usd          = models.DecimalField(max_digits=8, decimal_places=2)
    original_price_usd = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    coins_per_month    = models.PositiveIntegerField()
    bonus_coins        = models.PositiveIntegerField(default=0)
    badge              = models.CharField(max_length=100, blank=True, null=True)
    is_primary         = models.BooleanField(default=False)
    sub_title          = models.CharField(max_length=200, blank=True, null=True)
    discount_pct       = models.PositiveSmallIntegerField(default=0)
    duration_days      = models.PositiveIntegerField(default=30)
    stripe_price_id    = models.CharField(max_length=100, blank=True)
    is_active          = models.BooleanField(default=True)

    class Meta:
        db_table = 'subscription_plans'

    def __str__(self):
        return self.label


class Purchase(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED    = 'failed'
    STATUS_REFUNDED  = 'refunded'
    STATUS_CHOICES   = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED,    'Failed'),
        (STATUS_REFUNDED,  'Refunded'),
    ]

    TYPE_COIN_PACK   = 'coin_pack'
    TYPE_SUBSCRIPTION= 'subscription'
    TYPE_CHOICES     = [
        (TYPE_COIN_PACK,    'Coin Pack'),
        (TYPE_SUBSCRIPTION, 'Subscription'),
    ]

    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    purchase_type     = models.CharField(max_length=15, choices=TYPE_CHOICES)
    coin_package      = models.ForeignKey(CoinPackage, on_delete=models.SET_NULL, null=True, blank=True)
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    coins_granted     = models.PositiveIntegerField(default=0)
    amount_paid_usd   = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_id  = models.CharField(max_length=200, blank=True)
    stripe_session_id  = models.CharField(max_length=200, blank=True)
    iap_transaction_id = models.CharField(max_length=200, blank=True, db_index=True)
    status             = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at        = models.DateTimeField(auto_now_add=True)
    completed_at      = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'purchases'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.purchase_type} - {self.status}'


class Subscription(models.Model):
    user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan               = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    stripe_sub_id      = models.CharField(max_length=200, blank=True)
    started_at         = models.DateTimeField(auto_now_add=True)
    expires_at         = models.DateTimeField()
    is_active          = models.BooleanField(default=True)
    auto_renew         = models.BooleanField(default=True)
    cancelled_at       = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'subscriptions'

    def __str__(self):
        return f'{self.user.username} - {self.plan}'


class AuthorPayout(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_PROCESSED = 'processed'
    STATUS_FAILED    = 'failed'
    STATUS_CHOICES   = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_PROCESSED, 'Processed'),
        (STATUS_FAILED,    'Failed'),
    ]

    author        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    amount_usd    = models.DecimalField(max_digits=10, decimal_places=2)
    coins_total   = models.PositiveIntegerField()
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payout_method = models.CharField(max_length=50, blank=True)
    reference     = models.CharField(max_length=200, blank=True)
    notes         = models.TextField(blank=True)
    requested_at  = models.DateTimeField(auto_now_add=True)
    processed_at  = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'author_payouts'
        ordering = ['-requested_at']


# class DailyRewardClaim(models.Model):
#     user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     claim_type = models.CharField(max_length=50)  # checkin|reading|ad|signin|notification
#     coins      = models.IntegerField()
#     claimed_at = models.DateField(auto_now_add=True)
#     class Meta:
#         unique_together = ('user', 'claim_type', 'claimed_at')

# class ReadingSession(models.Model):
#     user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     story     = models.ForeignKey('stories.Story', on_delete=models.CASCADE, null=True)
#     chapter   = models.IntegerField(default=1)
#     minutes   = models.IntegerField(default=0)
#     date      = models.DateField(auto_now_add=True)

# class ReadingSchedule(models.Model):
#     user              = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     enabled           = models.BooleanField(default=False)
#     hour              = models.IntegerField(default=21)
#     minute            = models.IntegerField(default=0)
#     days              = models.JSONField(default=list)  # [True,True,True,True,True,True,True]
#     goal_minutes      = models.IntegerField(default=30)
#     goal_reminder     = models.BooleanField(default=True)
#     updated_at        = models.DateTimeField(auto_now=True)



 
class DailyRewardClaim(models.Model):
    """Tracks every coin reward claim to prevent double-claiming"""
    CLAIM_TYPES = [
        ('checkin',      'Daily Check-in'),
        ('reading_5',    'Reading 5 min'),
        ('reading_10',   'Reading 10 min'),
        ('reading_30',   'Reading 30 min'),
        ('reading_60',   'Reading 60 min'),
        ('reading_120',  'Reading 120 min'),
        ('reading_180',  'Reading 180 min'),
        ('ad',           'Watch Ad'),
        ('signin',       'Sign In Reward'),
        ('notification', 'Notification Reward'),
    ]
    user       = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='reward_claims')
    claim_type = models.CharField(max_length=50, choices=CLAIM_TYPES)
    coins      = models.IntegerField()
    claimed_at = models.DateField(auto_now_add=True)
 
    class Meta:
        ordering = ['-claimed_at']
 
    def __str__(self):
        return f'{self.user.username} — {self.claim_type} — {self.coins} coins'
 
 
class ReadingSession(models.Model):
    """Tracks daily reading time per user"""
    user    = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name='reading_sessions')
    story   = models.ForeignKey('stories.Story', on_delete=models.SET_NULL,
                                null=True, blank=True)
    chapter = models.IntegerField(default=1)
    minutes = models.IntegerField(default=0)
    date    = models.DateField(auto_now_add=True)
 
    class Meta:
        ordering = ['-date']
 
    def __str__(self):
        return f'{self.user.username} — {self.date} — {self.minutes} min'
 
 
class ReadingSchedule(models.Model):
    """User's reading schedule settings"""
    user          = models.OneToOneField(settings.AUTH_USER_MODEL,
                                          on_delete=models.CASCADE,
                                          related_name='reading_schedule')
    enabled       = models.BooleanField(default=False)
    hour          = models.IntegerField(default=21)
    minute        = models.IntegerField(default=0)
    days          = models.JSONField(default=list)
    goal_minutes  = models.IntegerField(default=30)
    goal_reminder = models.BooleanField(default=True)
    updated_at    = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return f'{self.user.username} — {self.hour}:{self.minute:02d}'
 

# Coins awarded per consecutive check-in day (cycles every 7 days)
STREAK_REWARDS = [10, 15, 20, 25, 30, 35, 40]


class CheckinStreak(models.Model):
    """Persists each user's check-in streak so we don't recompute from history every time."""
    user           = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checkin_streak')
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_checkin   = models.DateField(null=True, blank=True)
    total_checkins = models.PositiveIntegerField(default=0)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'checkin_streaks'

    def __str__(self):
        return f'{self.user.username} — streak {self.current_streak}'

    def next_reward(self):
        """Coins the user will earn on their NEXT check-in."""
        day_index = self.current_streak % len(STREAK_REWARDS)
        return STREAK_REWARDS[day_index]

    def todays_reward(self):
        """Coins earned on today's check-in (streak already incremented)."""
        day_index = (self.current_streak - 1) % len(STREAK_REWARDS)
        return STREAK_REWARDS[max(day_index, 0)]


class Task(models.Model):
    TYPE_ACTION   = 'action'
    TYPE_RESPONSE = 'response'
    TYPE_CHOICES  = [
        (TYPE_ACTION,   'Action'),
        (TYPE_RESPONSE, 'Response'),
    ]

    title        = models.CharField(max_length=200)
    description  = models.TextField()
    task_type    = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_ACTION)
    reward_coins = models.PositiveIntegerField(default=10)
    icon         = models.CharField(max_length=10, blank=True, help_text='Emoji icon, e.g. 📖')
    is_active    = models.BooleanField(default=True, db_index=True)
    is_repeatable= models.BooleanField(default=False, help_text='Can a user complete this more than once?')
    expires_at   = models.DateTimeField(null=True, blank=True, help_text='Leave blank for no expiry')
    order        = models.PositiveSmallIntegerField(default=0)
    created_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tasks_created')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tasks'
        ordering = ['order', '-created_at']

    def __str__(self):
        return f'[{self.task_type}] {self.title} ({self.reward_coins} coins)'


class UserTask(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_CLAIMED   = 'claimed'
    STATUS_CHOICES   = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CLAIMED,   'Claimed'),
    ]

    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_tasks')
    task         = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='completions')
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    response     = models.TextField(blank=True, help_text='User-submitted text for response-type tasks')
    completed_at = models.DateTimeField(null=True, blank=True)
    claimed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_tasks'
        unique_together = ('user', 'task')

    def __str__(self):
        return f'{self.user.username} — {self.task.title} [{self.status}]'


class ReadingHistory(models.Model):
    # \"\"\"Tracks every story a user has opened, with last chapter read.\"\"\"
    user           = models.ForeignKey(settings.AUTH_USER_MODEL,
                         on_delete=models.CASCADE,
                         related_name='reading_history')
    story          = models.ForeignKey('stories.Story',
                         on_delete=models.CASCADE,
                         related_name='history_entries')
    chapter_number = models.PositiveIntegerField(default=1)
    chapter_title  = models.CharField(max_length=300, blank=True, default='')
    read_at        = models.DateTimeField(auto_now=True)
 
    class Meta:
        ordering             = ['-read_at']
        unique_together      = ('user', 'story')   # one row per story
        verbose_name_plural  = 'Reading history'
 
    def __str__(self):
        return f'{self.user.username} — {self.story.title} ch.{self.chapter_number}'