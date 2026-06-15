from django.db import models
from django.conf import settings
from django.utils.text import slugify


class BlogCategory(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    slug        = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='blog_categories_created',
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Blog Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    STATUS_DRAFT     = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES   = [(STATUS_DRAFT, 'Draft'), (STATUS_PUBLISHED, 'Published')]

    AUDIENCE_PUBLIC  = 'public'
    AUDIENCE_AUTHORS = 'authors'
    AUDIENCE_CHOICES = [(AUDIENCE_PUBLIC, 'Everyone'), (AUDIENCE_AUTHORS, 'Authors only')]

    title       = models.CharField(max_length=300)
    slug        = models.SlugField(max_length=320, unique=True, blank=True)
    excerpt     = models.TextField(max_length=500, blank=True, help_text='Short summary shown in listings')
    content     = models.TextField(help_text='HTML content from the editor')
    cover_image = models.ImageField(upload_to='blog/covers/', blank=True, null=True)
    category    = models.ForeignKey(
        BlogCategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='posts',
    )
    author      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='blog_posts',
    )
    status      = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    audience    = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default=AUDIENCE_PUBLIC,
                                   help_text='Who can read this article')
    tags        = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags')
    views       = models.PositiveIntegerField(default=0)
    read_time   = models.PositiveSmallIntegerField(default=1, help_text='Estimated minutes to read')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or 'post'
            slug, n = base, 1
            while BlogPost.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        # auto estimate read time (~200 words/min)
        import re
        words = len(re.sub(r'<[^>]+>', '', self.content).split())
        self.read_time = max(1, round(words / 200))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class BlogLike(models.Model):
    post       = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='likes')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')
        db_table = 'blog_likes'

    def __str__(self):
        return f'{self.user} liked {self.post}'


class BlogComment(models.Model):
    post       = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_comments')
    content    = models.TextField(max_length=1000)
    parent     = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        db_table = 'blog_comments'

    def __str__(self):
        return f'{self.user} on {self.post}'
