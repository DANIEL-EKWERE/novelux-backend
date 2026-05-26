# models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Comment(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    story           = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='comments')
    chapter         = models.ForeignKey('chapters.Chapter', on_delete=models.CASCADE,
                                        related_name='comments', null=True, blank=True)
    parent          = models.ForeignKey('self', on_delete=models.CASCADE,
                                        related_name='replies', null=True, blank=True)
    paragraph_index = models.PositiveIntegerField(null=True, blank=True,
                                                   help_text='For inline/paragraph-level comments')
    content         = models.TextField(max_length=2000)
    likes_count     = models.PositiveIntegerField(default=0)
    is_pinned       = models.BooleanField(default=False)
    is_flagged      = models.BooleanField(default=False)
    is_author_reply = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'comments'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.content[:50]}'


class CommentLike(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    comment    = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table      = 'comment_likes'
        unique_together = ('user', 'comment')
