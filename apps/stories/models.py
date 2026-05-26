# from django.db import models
# from django.contrib.auth import get_user_model

# from config import settings

# User = get_user_model()


# class Genre(models.Model):
#     name        = models.CharField(max_length=50, unique=True)
#     slug        = models.SlugField(unique=True)
#     description = models.TextField(blank=True)
#     cover_image = models.ImageField(upload_to='genres/', blank=True, null=True)

#     class Meta:
#         db_table = 'genres'

#     def __str__(self):
#         return self.name


# class Tag(models.Model):
#     name = models.CharField(max_length=50, unique=True)
#     slug = models.SlugField(unique=True)

#     class Meta:
#         db_table = 'tags'

#     def __str__(self):
#         return self.name


# class Story(models.Model):
#     STATUS_DRAFT     = 'draft'
#     STATUS_ONGOING   = 'ongoing'
#     STATUS_COMPLETED = 'completed'
#     STATUS_PAUSED    = 'paused'
#     STATUS_CHOICES   = [
#         (STATUS_DRAFT,     'Draft'),
#         (STATUS_ONGOING,   'Ongoing'),
#         (STATUS_COMPLETED, 'Completed'),
#         (STATUS_PAUSED,    'Paused'),
#     ]

#     LANG_CHOICES = [
#         ('en', 'English'), ('fr', 'French'), ('es', 'Spanish'),
#         ('pt', 'Portuguese'), ('yo', 'Yoruba'), ('ig', 'Igbo'),
#         ('ha', 'Hausa'), ('sw', 'Swahili'), ('ar', 'Arabic'),
#         ('zh', 'Chinese'),
#     ]

#     GENDER_CHOICES = [
#         ('male',             'Male'),
#         ('female',           'Female'),
#         ('prefer_not_to_say','Prefer not to say'),
#     ]
#     gender           = models.CharField(max_length=30, choices=GENDER_CHOICES,
#                            blank=True, default='')
#     author          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
#     title           = models.CharField(max_length=255)
#     slug            = models.SlugField(unique=True, max_length=300)
#     description     = models.TextField()
#     cover_image     = models.ImageField(upload_to='covers/', blank=True, null=True)
#     genre           = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, related_name='stories')
#     tags            = models.ManyToManyField(Tag, blank=True, related_name='stories')
#     language        = models.CharField(max_length=5, choices=LANG_CHOICES, default='en')
#     status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
#     is_exclusive    = models.BooleanField(default=False)
#     is_featured     = models.BooleanField(default=False)
#     is_editors_pick = models.BooleanField(default=False)
#     is_world_famous = models.BooleanField(default=False)
#     is_completed    = models.BooleanField(default=False)
#     is_free_download = models.BooleanField(default=False)
#     is_african_folktale      = models.BooleanField(default=False)

#     # Stats (denormalized for performance)
#     total_views     = models.PositiveIntegerField(default=0)
#     total_unlocks   = models.PositiveIntegerField(default=0)
#     total_chapters  = models.PositiveIntegerField(default=0)
#     average_rating  = models.DecimalField(max_digits=3, decimal_places=2, default=0)
#     total_ratings   = models.PositiveIntegerField(default=0)
#     total_comments  = models.PositiveIntegerField(default=0)
#     total_tips      = models.PositiveIntegerField(default=0)
#     word_count      = models.PositiveIntegerField(default=0)

#     # Scheduling
#     update_schedule = models.CharField(max_length=100, blank=True, help_text='e.g. Mon/Wed/Fri')
#     plot_summary    = models.TextField(blank=True)
#     created_at      = models.DateTimeField(auto_now_add=True)
#     updated_at      = models.DateTimeField(auto_now=True)
#     published_at    = models.DateTimeField(blank=True, null=True)

#     class Meta:
#         db_table  = 'stories'
#         ordering  = ['-created_at']
#         indexes   = [
#             models.Index(fields=['status', 'language']),
#             models.Index(fields=['genre', 'status']),
#             models.Index(fields=['-total_views']),
#         ]

#     def __str__(self):
#         return self.title


# class Bookmark(models.Model):
#     user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
#     story      = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='bookmarked_by')
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table      = 'bookmarks'
#         unique_together = ('user', 'story')


# class ReadingProgress(models.Model):
#     user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_progress')
#     story             = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='readers_progress')
#     last_chapter      = models.PositiveIntegerField(default=0)
#     last_paragraph    = models.PositiveIntegerField(default=0)
#     updated_at        = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table      = 'reading_progress'
#         unique_together = ('user', 'story')


# class Rating(models.Model):
#     user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
#     story      = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='ratings')
#     score      = models.PositiveSmallIntegerField()   # 1–5
#     review     = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table      = 'ratings'
#         unique_together = ('user', 'story')

#     def save(self, *args, **kwargs):
#         super().save(*args, **kwargs)
#         # Update story average
#         from django.db.models import Avg
#         agg = Rating.objects.filter(story=self.story).aggregate(avg=Avg('score'), total=models.Count('id'))
#         self.story.average_rating = agg['avg'] or 0
#         self.story.total_ratings  = agg['total']
#         self.story.save(update_fields=['average_rating', 'total_ratings'])


# class PromoBanner(models.Model):
#     title      = models.CharField(max_length=200)
#     image      = models.ImageField(upload_to='banners/', null=True, blank=True)
#     image_url  = models.URLField(blank=True, default='')
#     slug       = models.SlugField(blank=True, default='',
#                     help_text='Story slug to navigate to on tap')
#     color      = models.CharField(max_length=10, default='#C15F3C')
#     is_active  = models.BooleanField(default=True)
#     order      = models.PositiveIntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)
 
#     class Meta:
#         ordering = ['order']
 
#     def __str__(self):
#         return self.title
 
#     def get_image_url(self, request=None):
#         if self.image:
#             url = self.image.url
#             return request.build_absolute_uri(url) if request else url
#         return self.image_url
    

# class BookRequest(models.Model):
#     # \"\"\"Stores user requests for books not yet on the platform.\"\"\"
#     title      = models.CharField(max_length=300)
#     author     = models.CharField(max_length=200, blank=True, default='')
#     requested_by = models.ForeignKey(settings.AUTH_USER_MODEL,
#                        null=True, blank=True, on_delete=models.SET_NULL)
#     created_at = models.DateTimeField(auto_now_add=True)
 
#     class Meta:
#         ordering = ['-created_at']
 
#     def __str__(self):
#         return f'{self.title} (by {self.author or "unknown"})'


from django.db import models
from django.contrib.auth import get_user_model

from config import settings

User = get_user_model()


class Genre(models.Model):
    name        = models.CharField(max_length=50, unique=True)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='genres/', blank=True, null=True)

    class Meta:
        db_table = 'genres'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = 'tags'

    def __str__(self):
        return self.name


class Story(models.Model):
    STATUS_DRAFT     = 'draft'
    STATUS_ONGOING   = 'ongoing'
    STATUS_COMPLETED = 'completed'
    STATUS_PAUSED    = 'paused'
    STATUS_CHOICES   = [
        (STATUS_DRAFT,     'Draft'),
        (STATUS_ONGOING,   'Ongoing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_PAUSED,    'Paused'),
    ]

    LANG_CHOICES = [
        ('en', 'English'), ('fr', 'French'), ('es', 'Spanish'),
        ('pt', 'Portuguese'), ('yo', 'Yoruba'), ('ig', 'Igbo'),
        ('ha', 'Hausa'), ('sw', 'Swahili'), ('ar', 'Arabic'),
        ('zh', 'Chinese'),
    ]

    GENDER_CHOICES = [
        ('male',             'Male'),
        ('female',           'Female'),
        ('prefer_not_to_say','Prefer not to say'),

    ]
    contract_status = models.CharField(
        max_length=20,
        choices=[
            ('none',                'None'),
            ('under_review',        'Under Review'),
            ('contract_sent',       'Contract Sent'),
            ('awaiting_signature',  'Awaiting Signature'),
            ('signed',              'Signed'),
            ('rejected',            'Rejected'),
        ],
        default='none',
    )
    contract_eligible = models.BooleanField(
        default=False,
        help_text='True when chapter threshold is hit and author can apply for contract.',
    )
    gender           = models.CharField(max_length=30, choices=GENDER_CHOICES,
                           blank=True, default='')
    author          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    title           = models.CharField(max_length=255)
    slug            = models.SlugField(unique=True, max_length=300)
    description     = models.TextField()
    cover_image     = models.ImageField(upload_to='covers/', blank=True, null=True)
    genre           = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, related_name='stories')
    tags            = models.ManyToManyField(Tag, blank=True, related_name='stories')
    language        = models.CharField(max_length=5, choices=LANG_CHOICES, default='en')
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_exclusive    = models.BooleanField(default=False)
    is_featured     = models.BooleanField(default=False)
    is_editors_pick = models.BooleanField(default=False)
    is_world_famous = models.BooleanField(default=False)
    is_completed    = models.BooleanField(default=False)
    is_free_download = models.BooleanField(default=False)
    is_african_folktale      = models.BooleanField(default=False)

    # Stats (denormalized for performance)
    total_views     = models.PositiveIntegerField(default=0)
    total_unlocks   = models.PositiveIntegerField(default=0)
    total_chapters  = models.PositiveIntegerField(default=0)
    average_rating  = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_ratings   = models.PositiveIntegerField(default=0)
    total_comments  = models.PositiveIntegerField(default=0)
    total_tips      = models.PositiveIntegerField(default=0)
    word_count      = models.PositiveIntegerField(default=0)

    # Editorial override — CE can set a custom threshold for this story.
    # If null, the global PlatformSettings threshold is used instead.
    review_threshold_override = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Override the global review threshold for this story only. Leave blank to use the platform default.',
    )

    synopsis        = models.TextField(blank=True, default='', help_text='Short hook shown on the story listing page.')
    story_outline   = models.TextField(blank=True, default='', help_text='Full narrative outline: how the story begins, develops, and ends. Used by SEs during review.')

    # Scheduling
    update_schedule   = models.CharField(max_length=100, blank=True, help_text='e.g. Mon/Wed/Fri')
    plot_summary      = models.TextField(blank=True)
    target_word_count = models.CharField(max_length=50, blank=True, default='')
    target_audience   = models.CharField(max_length=50, blank=True, default='')
    characters        = models.JSONField(default=list, blank=True)
    external_link     = models.URLField(max_length=500, blank=True, default='', help_text='Link to this story on another platform, e.g. Wattpad, AO3.')
    words_at_signing  = models.PositiveIntegerField(default=0, help_text='word_count snapshot taken when contract was signed; used to measure post-contract words only.')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    published_at    = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table  = 'stories'
        ordering  = ['-created_at']
        indexes   = [
            models.Index(fields=['status', 'language']),
            models.Index(fields=['genre', 'status']),
            models.Index(fields=['-total_views']),
        ]

    def __str__(self):
        return self.title


class Bookmark(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    story      = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table      = 'bookmarks'
        unique_together = ('user', 'story')


class ReadingProgress(models.Model):
    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_progress')
    story             = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='readers_progress')
    last_chapter      = models.PositiveIntegerField(default=0)
    last_paragraph    = models.PositiveIntegerField(default=0)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table      = 'reading_progress'
        unique_together = ('user', 'story')


class Rating(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    story      = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='ratings')
    score      = models.PositiveSmallIntegerField()   # 1–5
    review     = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table      = 'ratings'
        unique_together = ('user', 'story')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update story average
        from django.db.models import Avg
        agg = Rating.objects.filter(story=self.story).aggregate(avg=Avg('score'), total=models.Count('id'))
        self.story.average_rating = agg['avg'] or 0
        self.story.total_ratings  = agg['total']
        self.story.save(update_fields=['average_rating', 'total_ratings'])


class PromoBanner(models.Model):
    title      = models.CharField(max_length=200)
    image      = models.ImageField(upload_to='banners/', null=True, blank=True)
    image_url  = models.URLField(blank=True, default='')
    slug       = models.SlugField(blank=True, default='',
                    help_text='Story slug to navigate to on tap')
    color      = models.CharField(max_length=10, default='#C15F3C')
    is_active  = models.BooleanField(default=True)
    order      = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['order']
 
    def __str__(self):
        return self.title
 
    def get_image_url(self, request=None):
        if self.image:
            url = self.image.url
            return request.build_absolute_uri(url) if request else url
        return self.image_url
    

class BookRequest(models.Model):
    # \"\"\"Stores user requests for books not yet on the platform.\"\"\"
    title      = models.CharField(max_length=300)
    author     = models.CharField(max_length=200, blank=True, default='')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                       null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-created_at']
 
    def __str__(self):
        return f'{self.title} (by {self.author or "unknown"})'


class PlatformSettings(models.Model):
    """
    Singleton model — only one row should ever exist.
    Stores platform-wide configuration that admins can edit via Django admin.

    Access via:  PlatformSettings.get_threshold()
    Edit via:    /admin/stories/platformsettings/
    """
    review_threshold = models.PositiveSmallIntegerField(
        default=5,
        help_text=(
            'Number of chapters an author must upload before their first '
            'batch enters the SE review queue. Can be overridden per-story.'
        ),
    )
    post_contract_word_threshold = models.PositiveIntegerField(
        default=10000,
        help_text=(
            'Total word count a signed story must reach before it goes live '
            '(status → ongoing) and all held chapters are published. '
            'e.g. 10000 means the story needs 10 000 words total after signing.'
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = 'platform_settings'
        verbose_name = 'Platform Settings'

    def __str__(self):
        return f'Platform Settings (chapter threshold: {self.review_threshold}, word threshold: {self.post_contract_word_threshold})'

    @classmethod
    def get_threshold(cls):
        """Return the global chapter review threshold, creating the singleton if needed."""
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'review_threshold': 5})
        return obj.review_threshold

    @classmethod
    def get_word_threshold(cls):
        """Return the post-contract word count threshold, creating the singleton if needed."""
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'post_contract_word_threshold': 10000})
        return obj.post_contract_word_threshold

    def save(self, *args, **kwargs):
        # Enforce singleton — always use pk=1
        self.pk = 1
        super().save(*args, **kwargs)