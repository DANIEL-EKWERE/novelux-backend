from django.db import models
from django.conf import settings
from apps.stories.models import Story


RATING_CHOICES = [
    ('recommend', 'Recommend'),
    ('average',   'Average'),
    ('not_good',  'Not Good'),
]


class StoryReview(models.Model):
    story      = models.ForeignKey(Story, on_delete=models.CASCADE,
                                   related_name='reviews')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='reviews')
    rating     = models.CharField(max_length=20, choices=RATING_CHOICES,
                                  default='recommend')
    content    = models.TextField(blank=True, default='')
    likes      = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                        related_name='liked_reviews',
                                        blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # One review per user per story
        unique_together = ('story', 'user')
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.user.username} → {self.story.title} ({self.rating})'

    @property
    def likes_count(self):
        return self.likes.count()



class Report(models.Model):
    # review     = models.ForeignKey(StoryReview, on_delete=models.CASCADE,
    #                                related_name='reports')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='reports')
    phone     = models.CharField(max_length=20, blank=True)
    reason     = models.TextField()
    image     = models.ImageField(upload_to='review_reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One report per user per review
        unique_together = ('phone', 'user')
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.user.username} reported review {self.review.id}' 
    

class ReportMissingStory(models.Model):
    # review     = models.ForeignKey(StoryReview, on_delete=models.CASCADE,
    #                                related_name='reports')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='reports_missing_story')
    phone     = models.CharField(max_length=20, blank=True)
    reason     = models.TextField()
    image     = models.ImageField(upload_to='review_reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One report per user per review
        unique_together = ('phone', 'user')
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.user.username} reported review {self.review.id}'     