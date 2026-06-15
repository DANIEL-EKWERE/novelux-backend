# models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

TIP_AMOUNTS = [10, 50, 100, 500, 1000]


class Tip(models.Model):
    sender      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tips_sent')
    recipient   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tips_received')
    story       = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='tips')
    chapter     = models.ForeignKey('chapters.Chapter', on_delete=models.CASCADE,
                                    related_name='tips', null=True, blank=True)
    coins_amount= models.PositiveIntegerField()
    message     = models.CharField(max_length=255, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tips'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.sender.username} tipped {self.coins_amount} coins to {self.recipient.username}'
