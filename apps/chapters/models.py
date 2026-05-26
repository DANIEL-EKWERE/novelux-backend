# # from django.db import models
# # from django.contrib.auth import get_user_model
# # from ckeditor.fields import RichTextField

# # User = get_user_model()

# # from html.parser import HTMLParser

# # class HTMLStripper(HTMLParser):
# #     def __init__(self):
# #         super().__init__()
# #         self.reset()
# #         self.fed = []
# #     def handle_data(self, d):
# #         self.fed.append(d)
# #     def get_data(self):
# #         return ' '.join(self.fed)

# # def strip_html(html):
# #     s = HTMLStripper()
# #     s.feed(html or '')
# #     return s.get_data()

# # def count_words(html):
# #     text = strip_html(html)
# #     return len([w for w in text.split() if w.strip()])



# # import re
# # import bleach

# # ALLOWED_TAGS = [
# #     'p', 'br', 'strong', 'em', 'u', 's', 'h1', 'h2', 'h3',
# #     'ul', 'ol', 'li', 'blockquote', 'span', 'div',
# # ]

# # ALLOWED_ATTRS = {
# #     '*': ['style'],
# #     'a': ['href', 'title'],
# # }

# # def strip_html(html: str) -> str:
# #     """Remove all HTML tags, returning plain text."""
# #     return re.sub(r'<[^>]+>', ' ', html or '')

# # def clean_chapter_content(html: str) -> str:
# #     """Sanitise HTML: remove disallowed tags and strip hardcoded black/white colors."""
# #     cleaned = bleach.clean(html or '', tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
# #     cleaned = re.sub(
# #         r'color\s*:\s*(#000(000)?|#fff(fff)?|black|white|rgb\(0,\s*0,\s*0\)|rgb\(255,\s*255,\s*255\))\s*;?',
# #         '',
# #         cleaned,
# #         flags=re.IGNORECASE,
# #     )
# #     return cleaned

# # def count_words(html: str) -> int:
# #     """Count words from HTML content by stripping tags first."""
# #     plain = strip_html(html)
# #     return len(plain.split())


# # class Chapter(models.Model):
# #     story          = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='chapters')
# #     title          = models.CharField(max_length=255)
# #     chapter_number = models.PositiveIntegerField()
# #     content        = RichTextField()
# #     word_count     = models.PositiveIntegerField(default=0)
# #     is_locked      = models.BooleanField(default=True)
# #     coin_cost      = models.PositiveSmallIntegerField(default=20)
# #     is_published   = models.BooleanField(default=False)
# #     views          = models.PositiveIntegerField(default=0)
# #     unlocks        = models.PositiveIntegerField(default=0)
# #     scheduled_at   = models.DateTimeField(blank=True, null=True)
# #     created_at     = models.DateTimeField(auto_now_add=True)
# #     updated_at     = models.DateTimeField(auto_now=True)

# #     @property
# #     def estimated_read_minutes(self):
# #         return max(1, self.word_count // 200)

# #     class Meta:
# #         db_table        = 'chapters'
# #         ordering        = ['chapter_number']
# #         unique_together = ('story', 'chapter_number')

# #     def __str__(self):
# #         return f'{self.story.title} — Ch.{self.chapter_number}: {self.title}'

# #     def save(self, *args, **kwargs):
# #         self.content    = clean_chapter_content(self.content)   # sanitise before saving
# #         self.word_count = count_words(self.content)             # count from clean HTML
# #         super().save(*args, **kwargs)

# #         from apps.stories.models import Story
# #         Story.objects.filter(pk=self.story_id).update(
# #             total_chapters=Chapter.objects.filter(
# #                 story_id=self.story_id, is_published=True
# #             ).count(),
# #             word_count=Chapter.objects.filter(
# #                 story_id=self.story_id
# #             ).aggregate(
# #                 total=models.Sum('word_count')
# #             )['total'] or 0,
# #         )



# # # class Chapter(models.Model):
# # #     story        = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='chapters')
# # #     title        = models.CharField(max_length=255)
# # #     chapter_number = models.PositiveIntegerField()
# # #     content      = RichTextField()#= models.TextField()
# # #     word_count   = models.PositiveIntegerField(default=0)
# # #     is_locked    = models.BooleanField(default=True)
# # #     coin_cost    = models.PositiveSmallIntegerField(default=20)
# # #     is_published = models.BooleanField(default=False)
# # #     views        = models.PositiveIntegerField(default=0)
# # #     unlocks      = models.PositiveIntegerField(default=0)
# # #     scheduled_at = models.DateTimeField(blank=True, null=True)
# # #     created_at   = models.DateTimeField(auto_now_add=True)
# # #     updated_at   = models.DateTimeField(auto_now=True)

# # #     @property
# # #     def estimated_read_minutes(self):
# # #         return max(1, self.word_count // 200)
          

# # #     class Meta:
# # #         db_table      = 'chapters'
# # #         ordering      = ['chapter_number']
# # #         unique_together = ('story', 'chapter_number')

# # #     def __str__(self):
# # #         return f'{self.story.title} — Ch.{self.chapter_number}: {self.title}'

# # #     def save(self, *args, **kwargs):
# # #        self.word_count = count_words(self.content)  # ← replaces len(self.content.split())
# # #        super().save(*args, **kwargs)
# # #        # Update story word count and chapter count
# # #        from apps.stories.models import Story
# # #        Story.objects.filter(pk=self.story_id).update(
# # #            total_chapters=Chapter.objects.filter(story_id=self.story_id, is_published=True).count(),
# # #            word_count=Chapter.objects.filter(story_id=self.story_id).aggregate(
# # #                total=models.Sum('word_count')
# # #            )['total'] or 0
# # #        )
# # """
# #       @property
# #       def estimated_read_minutes(self):
# #           return max(1, self.word_count // 200)
# # """

# # class ChapterUnlock(models.Model):
# #     user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unlocked_chapters')
# #     chapter    = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='unlocked_by')
# #     coins_spent= models.PositiveSmallIntegerField()
# #     created_at = models.DateTimeField(auto_now_add=True)

# #     class Meta:
# #         db_table      = 'chapter_unlocks'
# #         unique_together = ('user', 'chapter')


# # class FreeChapterSchedule(models.Model):
# #     """One free chapter per story per day for a user."""
# #     user       = models.ForeignKey(User, on_delete=models.CASCADE)
# #     story      = models.ForeignKey('stories.Story', on_delete=models.CASCADE)
# #     date       = models.DateField(auto_now_add=True)
# #     chapter    = models.ForeignKey(Chapter, on_delete=models.CASCADE)

# #     class Meta:
# #         db_table      = 'free_chapter_schedules'
# #         unique_together = ('user', 'story', 'date')

# from django.db import models
# from django.contrib.auth import get_user_model
# from ckeditor.fields import RichTextField

# User = get_user_model()

# from html.parser import HTMLParser

# class HTMLStripper(HTMLParser):
#     def __init__(self):
#         super().__init__()
#         self.reset()
#         self.fed = []
#     def handle_data(self, d):
#         self.fed.append(d)
#     def get_data(self):
#         return ' '.join(self.fed)

# def strip_html(html):
#     s = HTMLStripper()
#     s.feed(html or '')
#     return s.get_data()

# def count_words(html):
#     text = strip_html(html)
#     return len([w for w in text.split() if w.strip()])


# class Chapter(models.Model):
#     story        = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='chapters')
#     title        = models.CharField(max_length=255)
#     chapter_number = models.PositiveIntegerField()
#     content      = RichTextField()
#     word_count   = models.PositiveIntegerField(default=0)
#     is_locked    = models.BooleanField(default=True)
#     coin_cost    = models.PositiveSmallIntegerField(default=20)
#     is_published = models.BooleanField(default=False)

#     # ── Editorial workflow status ─────────────────────────────────────────────
#     #
#     # Flow for authors WITHOUT a contract:
#     #   draft → submitted → pending_review (threshold hit) →
#     #   se_reviewing → se_revision (back to author) OR se_approved →
#     #   contract_sent → contracted → published
#     #
#     # Flow for authors WITH a contract (has_contract=True on AuthorProfile):
#     #   draft → published  (immediate, no review)
#     #
#     STATUS_DRAFT          = 'draft'           # author is still writing
#     STATUS_SUBMITTED      = 'submitted'       # author saved/submitted, awaiting threshold
#     STATUS_PENDING_REVIEW = 'pending_review'  # threshold hit — in SE queue
#     STATUS_SE_REVIEWING   = 'se_reviewing'    # SE has opened and is actively reviewing
#     STATUS_SE_REVISION    = 'se_revision'     # SE sent back to author for edits
#     STATUS_SE_APPROVED    = 'se_approved'     # SE approved — CE can now send contract
#     STATUS_CONTRACT_SENT  = 'contract_sent'   # CE sent contract, awaiting author signature
#     STATUS_CONTRACTED     = 'contracted'      # author signed contract
#     STATUS_PUBLISHED      = 'published'       # live on platform
#     STATUS_REJECTED       = 'rejected'        # removed / does not meet standards

#     STATUS_CHOICES = [
#         (STATUS_DRAFT,          'Draft'),
#         (STATUS_SUBMITTED,      'Submitted'),
#         (STATUS_PENDING_REVIEW, 'Pending SE Review'),
#         (STATUS_SE_REVIEWING,   'SE Reviewing'),
#         (STATUS_SE_REVISION,    'Revision Requested by SE'),
#         (STATUS_SE_APPROVED,    'SE Approved'),
#         (STATUS_CONTRACT_SENT,  'Contract Sent'),
#         (STATUS_CONTRACTED,     'Contracted'),
#         (STATUS_PUBLISHED,      'Published'),
#         (STATUS_REJECTED,       'Rejected'),
#     ]

#     status = models.CharField(
#         max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
#         db_index=True,
#     )

#     # ── SE review fields ──────────────────────────────────────────────────────
#     reviewed_by_se  = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='se_reviewed_chapters',
#         limit_choices_to={'role': 'se'},
#     )
#     se_note         = models.TextField(
#         blank=True,
#         help_text='SE feedback visible to the author — revision notes or approval message.',
#     )
#     reviewed_at     = models.DateTimeField(null=True, blank=True)

#     views        = models.PositiveIntegerField(default=0)
#     unlocks      = models.PositiveIntegerField(default=0)
#     scheduled_at = models.DateTimeField(blank=True, null=True)
#     created_at   = models.DateTimeField(auto_now_add=True)
#     updated_at   = models.DateTimeField(auto_now=True)

#     @property
#     def estimated_read_minutes(self):
#         return max(1, self.word_count // 200)

#     class Meta:
#         db_table      = 'chapters'
#         ordering      = ['chapter_number']
#         unique_together = ('story', 'chapter_number')

#     def __str__(self):
#         return f'{self.story.title} — Ch.{self.chapter_number}: {self.title}'

#     def save(self, *args, **kwargs):
#         self.word_count = count_words(self.content)

#         # If the parent story has a signed contract, auto-publish this chapter
#         try:
#             from apps.stories.models import Story
#             st = Story.objects.get(pk=self.story_id)
#             if getattr(st, 'contract_status', None) == 'signed':
#                 self.status = self.STATUS_PUBLISHED
#                 self.is_published = True
#         except Exception:
#             # If story lookup fails for any reason, continue without raising.
#             pass

#         super().save(*args, **kwargs)

#         # Auto-trigger review threshold or auto-publish contracted authors
#         self._check_editorial_trigger()

#         from apps.stories.models import Story
#         Story.objects.filter(pk=self.story_id).update(
#             total_chapters=Chapter.objects.filter(story_id=self.story_id).count(),
#             word_count=Chapter.objects.filter(story_id=self.story_id).aggregate(
#                 total=models.Sum('word_count')
#             )['total'] or 0
#         )
        

#     def _check_editorial_trigger(self):
#         """
#         Called after every save.

#         Case A — author has a signed contract:
#             Any chapter saved as 'submitted' is immediately published.

#         Case B — author has NO contract yet:
#             Count how many submitted/draft chapters this story has.
#             Once the count hits the platform threshold, flip ALL of them
#             to 'pending_review' so they enter the SE queue together.
#             The threshold is set globally in PlatformSettings (default 5)
#             but can be overridden per-story via Story.review_threshold_override.
#         """
#         from apps.stories.models import Story, PlatformSettings
#         try:
#             story   = Story.objects.select_related('author__author_profile').get(pk=self.story_id)
#             profile = story.author.author_profile
#         except Exception:
#             return

#         # Case A: contracted author — publish immediately
#         if profile.has_contract and self.status == self.STATUS_SUBMITTED:
#             Chapter.objects.filter(pk=self.pk).update(
#                 status=self.STATUS_PUBLISHED,
#                 is_published=True,
#             )
#             return

#         # Case B: no contract — check threshold
#         if profile.has_contract:
#             return  # already handled above or not submitted

#         # Determine threshold (story override → platform setting → hard default)
#         threshold = (
#             story.review_threshold_override
#             if story.review_threshold_override
#             else PlatformSettings.get_threshold()
#         )

#         # Count ALL chapters on this story (regardless of status)
#         # so that the threshold fires correctly even if some chapters
#         # have already moved past draft/submitted in a prior cycle.
#         pool_count = Chapter.objects.filter(story=story).count()

#         if pool_count >= threshold:
#             # Mark story as contract-eligible so the dashboard shows the Apply button.
#             # Do NOT auto-submit — the author must click Apply manually.
#             Story.objects.filter(pk=story.pk).update(contract_eligible=True)

#             # Notify the author once (only on the exact chapter that hits the threshold)
#             if pool_count == threshold:
#                 try:
#                     from apps.notifications.services import notify_user
#                     notify_user(
#                         story.author,
#                         title='Your story is ready for a contract! 🎉',
#                         body=f'"{story.title}" has reached {threshold} chapters. Go to My Books to apply.',
#                         data={'screen': 'my_books', 'slug': story.slug, 'action': 'apply_contract'},
#                     )
#                 except Exception:
#                     pass

#     @classmethod
#     def publish_held_chapters_for_author(cls, author):
#         held_statuses = [
#             cls.STATUS_DRAFT,
#             cls.STATUS_SUBMITTED,
#             cls.STATUS_PENDING_REVIEW,
#             cls.STATUS_SE_REVIEWING,
#             cls.STATUS_SE_REVISION,
#             cls.STATUS_SE_APPROVED,
#             cls.STATUS_CONTRACT_SENT,
#         ]
#         held_qs = cls.objects.filter(
#             story__author=author,
#             status__in=held_statuses,
#             is_published=False,
#         )
#         story_ids = list(held_qs.values_list('story_id', flat=True).distinct())
#         published_count = held_qs.update(
#             status=cls.STATUS_PUBLISHED,
#             is_published=True,
#         )

#         from apps.stories.models import Story

#         # Always mark all this author's contract-eligible stories as ongoing/signed
#         # regardless of whether chapters were found above
#         Story.objects.filter(
#             author=author,
#         ).exclude(
#             contract_status='none',
#         ).update(
#             status='ongoing',
#             contract_status='signed',
#         )

#         # Recalculate chapter counts for affected stories
#         all_story_ids = list(
#             Story.objects.filter(author=author).exclude(contract_status='none')
#             .values_list('pk', flat=True)
#         )
#         for story_id in set(story_ids + all_story_ids):
#             Story.objects.filter(pk=story_id).update(
#                 total_chapters=Chapter.objects.filter(story_id=story_id).count(),
#                 word_count=Chapter.objects.filter(story_id=story_id).aggregate(
#                     total=models.Sum('word_count')
#                 )['total'] or 0
#             )
#         return published_count

# class ChapterUnlock(models.Model):
#     user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unlocked_chapters')
#     chapter    = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='unlocked_by')
#     coins_spent= models.PositiveSmallIntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table      = 'chapter_unlocks'
#         unique_together = ('user', 'chapter')


# class FreeChapterSchedule(models.Model):
#     """One free chapter per story per day for a user."""
#     user       = models.ForeignKey(User, on_delete=models.CASCADE)
#     story      = models.ForeignKey('stories.Story', on_delete=models.CASCADE)
#     date       = models.DateField(auto_now_add=True)
#     chapter    = models.ForeignKey(Chapter, on_delete=models.CASCADE)

#     class Meta:
#         db_table      = 'free_chapter_schedules'
#         unique_together = ('user', 'story', 'date')


# from django.db import models
# from django.contrib.auth import get_user_model
# from ckeditor.fields import RichTextField

# User = get_user_model()

# from html.parser import HTMLParser

# class HTMLStripper(HTMLParser):
#     def __init__(self):
#         super().__init__()
#         self.reset()
#         self.fed = []
#     def handle_data(self, d):
#         self.fed.append(d)
#     def get_data(self):
#         return ' '.join(self.fed)

# def strip_html(html):
#     s = HTMLStripper()
#     s.feed(html or '')
#     return s.get_data()

# def count_words(html):
#     text = strip_html(html)
#     return len([w for w in text.split() if w.strip()])



# import re
# import bleach

# ALLOWED_TAGS = [
#     'p', 'br', 'strong', 'em', 'u', 's', 'h1', 'h2', 'h3',
#     'ul', 'ol', 'li', 'blockquote', 'span', 'div',
# ]

# ALLOWED_ATTRS = {
#     '*': ['style'],
#     'a': ['href', 'title'],
# }

# def strip_html(html: str) -> str:
#     """Remove all HTML tags, returning plain text."""
#     return re.sub(r'<[^>]+>', ' ', html or '')

# def clean_chapter_content(html: str) -> str:
#     """Sanitise HTML: remove disallowed tags and strip hardcoded black/white colors."""
#     cleaned = bleach.clean(html or '', tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
#     cleaned = re.sub(
#         r'color\s*:\s*(#000(000)?|#fff(fff)?|black|white|rgb\(0,\s*0,\s*0\)|rgb\(255,\s*255,\s*255\))\s*;?',
#         '',
#         cleaned,
#         flags=re.IGNORECASE,
#     )
#     return cleaned

# def count_words(html: str) -> int:
#     """Count words from HTML content by stripping tags first."""
#     plain = strip_html(html)
#     return len(plain.split())


# class Chapter(models.Model):
#     story          = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='chapters')
#     title          = models.CharField(max_length=255)
#     chapter_number = models.PositiveIntegerField()
#     content        = RichTextField()
#     word_count     = models.PositiveIntegerField(default=0)
#     is_locked      = models.BooleanField(default=True)
#     coin_cost      = models.PositiveSmallIntegerField(default=20)
#     is_published   = models.BooleanField(default=False)
#     views          = models.PositiveIntegerField(default=0)
#     unlocks        = models.PositiveIntegerField(default=0)
#     scheduled_at   = models.DateTimeField(blank=True, null=True)
#     created_at     = models.DateTimeField(auto_now_add=True)
#     updated_at     = models.DateTimeField(auto_now=True)

#     @property
#     def estimated_read_minutes(self):
#         return max(1, self.word_count // 200)

#     class Meta:
#         db_table        = 'chapters'
#         ordering        = ['chapter_number']
#         unique_together = ('story', 'chapter_number')

#     def __str__(self):
#         return f'{self.story.title} — Ch.{self.chapter_number}: {self.title}'

#     def save(self, *args, **kwargs):
#         self.content    = clean_chapter_content(self.content)   # sanitise before saving
#         self.word_count = count_words(self.content)             # count from clean HTML
#         super().save(*args, **kwargs)

#         from apps.stories.models import Story
#         Story.objects.filter(pk=self.story_id).update(
#             total_chapters=Chapter.objects.filter(
#                 story_id=self.story_id, is_published=True
#             ).count(),
#             word_count=Chapter.objects.filter(
#                 story_id=self.story_id
#             ).aggregate(
#                 total=models.Sum('word_count')
#             )['total'] or 0,
#         )



# # class Chapter(models.Model):
# #     story        = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='chapters')
# #     title        = models.CharField(max_length=255)
# #     chapter_number = models.PositiveIntegerField()
# #     content      = RichTextField()#= models.TextField()
# #     word_count   = models.PositiveIntegerField(default=0)
# #     is_locked    = models.BooleanField(default=True)
# #     coin_cost    = models.PositiveSmallIntegerField(default=20)
# #     is_published = models.BooleanField(default=False)
# #     views        = models.PositiveIntegerField(default=0)
# #     unlocks      = models.PositiveIntegerField(default=0)
# #     scheduled_at = models.DateTimeField(blank=True, null=True)
# #     created_at   = models.DateTimeField(auto_now_add=True)
# #     updated_at   = models.DateTimeField(auto_now=True)

# #     @property
# #     def estimated_read_minutes(self):
# #         return max(1, self.word_count // 200)
          

# #     class Meta:
# #         db_table      = 'chapters'
# #         ordering      = ['chapter_number']
# #         unique_together = ('story', 'chapter_number')

# #     def __str__(self):
# #         return f'{self.story.title} — Ch.{self.chapter_number}: {self.title}'

# #     def save(self, *args, **kwargs):
# #        self.word_count = count_words(self.content)  # ← replaces len(self.content.split())
# #        super().save(*args, **kwargs)
# #        # Update story word count and chapter count
# #        from apps.stories.models import Story
# #        Story.objects.filter(pk=self.story_id).update(
# #            total_chapters=Chapter.objects.filter(story_id=self.story_id, is_published=True).count(),
# #            word_count=Chapter.objects.filter(story_id=self.story_id).aggregate(
# #                total=models.Sum('word_count')
# #            )['total'] or 0
# #        )
# """
#       @property
#       def estimated_read_minutes(self):
#           return max(1, self.word_count // 200)
# """

# class ChapterUnlock(models.Model):
#     user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unlocked_chapters')
#     chapter    = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='unlocked_by')
#     coins_spent= models.PositiveSmallIntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table      = 'chapter_unlocks'
#         unique_together = ('user', 'chapter')


# class FreeChapterSchedule(models.Model):
#     """One free chapter per story per day for a user."""
#     user       = models.ForeignKey(User, on_delete=models.CASCADE)
#     story      = models.ForeignKey('stories.Story', on_delete=models.CASCADE)
#     date       = models.DateField(auto_now_add=True)
#     chapter    = models.ForeignKey(Chapter, on_delete=models.CASCADE)

#     class Meta:
#         db_table      = 'free_chapter_schedules'
#         unique_together = ('user', 'story', 'date')

from django.db import models
from django.contrib.auth import get_user_model
from ckeditor.fields import RichTextField

User = get_user_model()

from html.parser import HTMLParser

class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ' '.join(self.fed)

def strip_html(html):
    s = HTMLStripper()
    s.feed(html or '')
    return s.get_data()

def count_words(html):
    text = strip_html(html)
    return len([w for w in text.split() if w.strip()])


class Chapter(models.Model):
    story        = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='chapters')
    title        = models.CharField(max_length=255)
    chapter_number = models.PositiveIntegerField()
    content      = RichTextField()
    word_count   = models.PositiveIntegerField(default=0)
    is_locked    = models.BooleanField(default=True)
    coin_cost    = models.PositiveSmallIntegerField(default=20)
    is_published = models.BooleanField(default=False)

    # ── Editorial workflow status ─────────────────────────────────────────────
    #
    # Flow for authors WITHOUT a contract:
    #   draft → submitted → pending_review (threshold hit) →
    #   se_reviewing → se_revision (back to author) OR se_approved →
    #   contract_sent → contracted → published
    #
    # Flow for authors WITH a contract (has_contract=True on AuthorProfile):
    #   draft → published  (immediate, no review)
    #
    STATUS_DRAFT          = 'draft'           # author is still writing
    STATUS_SUBMITTED      = 'submitted'       # author saved/submitted, awaiting threshold
    STATUS_PENDING_REVIEW = 'pending_review'  # threshold hit — in SE queue
    STATUS_SE_REVIEWING   = 'se_reviewing'    # SE has opened and is actively reviewing
    STATUS_SE_REVISION    = 'se_revision'     # SE sent back to author for edits
    STATUS_SE_APPROVED    = 'se_approved'     # SE approved — CE can now send contract
    STATUS_CONTRACT_SENT  = 'contract_sent'   # CE sent contract, awaiting author signature
    STATUS_CONTRACTED     = 'contracted'      # author signed contract
    STATUS_PUBLISHED      = 'published'       # live on platform
    STATUS_REJECTED       = 'rejected'        # removed / does not meet standards

    STATUS_CHOICES = [
        (STATUS_DRAFT,          'Draft'),
        (STATUS_SUBMITTED,      'Submitted'),
        (STATUS_PENDING_REVIEW, 'Pending SE Review'),
        (STATUS_SE_REVIEWING,   'SE Reviewing'),
        (STATUS_SE_REVISION,    'Revision Requested by SE'),
        (STATUS_SE_APPROVED,    'SE Approved'),
        (STATUS_CONTRACT_SENT,  'Contract Sent'),
        (STATUS_CONTRACTED,     'Contracted'),
        (STATUS_PUBLISHED,      'Published'),
        (STATUS_REJECTED,       'Rejected'),
    ]

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
        db_index=True,
    )

    # ── SE review fields ──────────────────────────────────────────────────────
    reviewed_by_se  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='se_reviewed_chapters',
        limit_choices_to={'role': 'se'},
    )
    se_note         = models.TextField(
        blank=True,
        help_text='SE feedback visible to the author — revision notes or approval message.',
    )
    reviewed_at     = models.DateTimeField(null=True, blank=True)

    views        = models.PositiveIntegerField(default=0)
    unlocks      = models.PositiveIntegerField(default=0)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    @property
    def estimated_read_minutes(self):
        return max(1, self.word_count // 200)

    class Meta:
        db_table      = 'chapters'
        ordering      = ['chapter_number']
        unique_together = ('story', 'chapter_number')

    def __str__(self):
        return f'{self.story.title} — Ch.{self.chapter_number}: {self.title}'

    def save(self, *args, **kwargs):
        self.word_count = count_words(self.content)
        super().save(*args, **kwargs)

        # Auto-trigger review threshold or auto-publish contracted authors
        self._check_editorial_trigger()

        from apps.stories.models import Story
        Story.objects.filter(pk=self.story_id).update(
            total_chapters=Chapter.objects.filter(story_id=self.story_id).count(),
            word_count=Chapter.objects.filter(story_id=self.story_id).aggregate(
                total=models.Sum('word_count')
            )['total'] or 0
        )

    def _check_editorial_trigger(self):
        """
        Called after every save.

        Case A — author has a signed contract:
            Any chapter saved as 'submitted' is immediately published.

        Case B — author has NO contract yet:
            Count how many submitted/draft chapters this story has.
            Once the count hits the platform threshold, flip ALL of them
            to 'pending_review' so they enter the SE queue together.
            The threshold is set globally in PlatformSettings (default 5)
            but can be overridden per-story via Story.review_threshold_override.
        """
        from apps.stories.models import Story, PlatformSettings
        try:
            story   = Story.objects.select_related('author__author_profile').get(pk=self.story_id)
            profile = story.author.author_profile
        except Exception:
            return

        # Case A: contracted author — check whether the story has hit the post-contract
        # word count threshold. If so, publish all held chapters and set the story live.
        if profile.has_contract:
            if story.contract_status != 'signed' or story.status == 'ongoing':
                return  # already live, or not yet fully signed — nothing to do

            from apps.stories.models import PlatformSettings
            word_threshold = PlatformSettings.get_word_threshold()
            # Count only words written AFTER signing by subtracting the snapshot
            # taken at signing time. This prevents pre-contract chapters from
            # immediately triggering the go-live threshold.
            total_words = Chapter.objects.filter(story=story).aggregate(
                total=models.Sum('word_count')
            )['total'] or 0
            post_contract_words = max(0, total_words - (story.words_at_signing or 0))

            if post_contract_words >= word_threshold:
                # Go live — publish all held chapters and mark story ongoing.
                Chapter.publish_held_chapters_for_author(story.author)
                try:
                    from apps.notifications.services import on_story_went_live
                    on_story_went_live(story.author, story)
                except Exception:
                    pass
            return

        # Case B: no contract — check chapter threshold

        # Determine threshold (story override → platform setting → hard default)
        threshold = (
            story.review_threshold_override
            if story.review_threshold_override
            else PlatformSettings.get_threshold()
        )

        # Count ALL chapters on this story (regardless of status)
        # so that the threshold fires correctly even if some chapters
        # have already moved past draft/submitted in a prior cycle.
        pool_count = Chapter.objects.filter(story=story).count()

        if pool_count >= threshold:
            # Mark story as contract-eligible so the dashboard shows the Apply button.
            # Do NOT auto-submit — the author must click Apply manually.
            Story.objects.filter(pk=story.pk).update(contract_eligible=True)

            # Notify the author once (only on the exact chapter that hits the threshold)
            if pool_count == threshold:
                try:
                    from apps.notifications.services import on_contract_threshold_reached
                    on_contract_threshold_reached(story.author, story)
                except Exception:
                    pass

    @classmethod
    def publish_held_chapters_for_author(cls, author):
        held_statuses = [
            cls.STATUS_DRAFT,
            cls.STATUS_SUBMITTED,
            cls.STATUS_PENDING_REVIEW,
            cls.STATUS_SE_REVIEWING,
            cls.STATUS_SE_REVISION,
            cls.STATUS_SE_APPROVED,
            cls.STATUS_CONTRACT_SENT,
        ]
        held_qs = cls.objects.filter(
            story__author=author,
            status__in=held_statuses,
            is_published=False,
        )
        story_ids = list(held_qs.values_list('story_id', flat=True).distinct())
        published_count = held_qs.update(
            status=cls.STATUS_PUBLISHED,
            is_published=True,
        )

        from apps.stories.models import Story

        # Always mark all this author's contract-eligible stories as ongoing/signed
        # regardless of whether chapters were found above
        Story.objects.filter(
            author=author,
        ).exclude(
            contract_status='none',
        ).update(
            status='ongoing',
            contract_status='signed',
        )

        # Recalculate chapter counts for affected stories
        all_story_ids = list(
            Story.objects.filter(author=author).exclude(contract_status='none')
            .values_list('pk', flat=True)
        )
        for story_id in set(story_ids + all_story_ids):
            Story.objects.filter(pk=story_id).update(
                total_chapters=Chapter.objects.filter(story_id=story_id).count(),
                word_count=Chapter.objects.filter(story_id=story_id).aggregate(
                    total=models.Sum('word_count')
                )['total'] or 0
            )
        return published_count

class ChapterUnlock(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unlocked_chapters')
    chapter    = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='unlocked_by')
    coins_spent= models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table      = 'chapter_unlocks'
        unique_together = ('user', 'chapter')


class FreeChapterSchedule(models.Model):
    """One free chapter per story per day for a user."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    story      = models.ForeignKey('stories.Story', on_delete=models.CASCADE)
    date       = models.DateField(auto_now_add=True)
    chapter    = models.ForeignKey(Chapter, on_delete=models.CASCADE)

    class Meta:
        db_table      = 'free_chapter_schedules'
        unique_together = ('user', 'story', 'date')