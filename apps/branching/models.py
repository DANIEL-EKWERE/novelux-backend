# models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BranchPoint(models.Model):
    """A decision point inside a chapter where the story can branch."""
    chapter     = models.ForeignKey('chapters.Chapter', on_delete=models.CASCADE,
                                    related_name='branch_points')
    prompt      = models.CharField(max_length=500, help_text='The choice question shown to readers')
    position    = models.PositiveIntegerField(help_text='Paragraph index where choice appears')
    voting_open = models.BooleanField(default=True)
    voting_ends = models.DateTimeField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'branch_points'
        ordering = ['position']

    def __str__(self):
        return f'BranchPoint in {self.chapter}: {self.prompt[:50]}'

    @property
    def total_votes(self):
        return self.choices.aggregate(
            total=models.Sum('votes_count')
        )['total'] or 0


class BranchChoice(models.Model):
    """One possible path at a BranchPoint."""
    branch_point    = models.ForeignKey(BranchPoint, on_delete=models.CASCADE, related_name='choices')
    label           = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    votes_count     = models.PositiveIntegerField(default=0)
    result_chapter  = models.ForeignKey('chapters.Chapter', on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='branch_sources',
                                         help_text='Chapter that follows if this choice wins')
    is_winner       = models.BooleanField(default=False)

    class Meta:
        db_table = 'branch_choices'

    def __str__(self):
        return self.label

    @property
    def vote_percentage(self):
        total = self.branch_point.total_votes
        return round((self.votes_count / total) * 100, 1) if total else 0


class BranchVote(models.Model):
    """Reader's vote at a BranchPoint."""
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='branch_votes')
    branch_point = models.ForeignKey(BranchPoint, on_delete=models.CASCADE)
    choice       = models.ForeignKey(BranchChoice, on_delete=models.CASCADE)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table      = 'branch_votes'
        unique_together = ('user', 'branch_point')

    def __str__(self):
        return f'{self.user.username} voted {self.choice.label}'
