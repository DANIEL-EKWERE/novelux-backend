# from rest_framework import generics, permissions, status
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from django.shortcuts import get_object_or_404
# from django.db.models import F
# from django.utils import timezone
# from .models import Chapter, ChapterUnlock, FreeChapterSchedule
# from .serializers import ChapterListSerializer, ChapterDetailSerializer, ChapterCreateUpdateSerializer
# from apps.stories.models import Story
# from apps.users.permissions import IsAuthorOrReadOnly
# from apps.notifications.tasks import notify_followers_new_chapter


# class ChapterListCreateView(generics.ListCreateAPIView):
#     def get_serializer_class(self):
#         return ChapterCreateUpdateSerializer if self.request.method == 'POST' else ChapterListSerializer

#     def get_permissions(self):
#         return [permissions.IsAuthenticated()] if self.request.method == 'POST' else [permissions.AllowAny()]

#     def get_queryset(self):
#         story = get_object_or_404(Story, slug=self.kwargs['story_slug'])
#         qs    = Chapter.objects.filter(story=story, is_published=True)
#         if self.request.user.is_authenticated and story.author == self.request.user:
#             qs = Chapter.objects.filter(story=story)
#         return qs

#     def perform_create(self, serializer):
#         from rest_framework.exceptions import PermissionDenied, ValidationError
#         story = get_object_or_404(Story, slug=self.kwargs['story_slug'])
#         if story.author != self.request.user:
#             raise PermissionDenied
#         # Block new chapters once the story hits threshold or author has applied
#         from apps.stories.models import PlatformSettings
#         threshold = (
#             story.review_threshold_override
#             if story.review_threshold_override
#             else PlatformSettings.get_threshold()
#         )
#         chapter_count = Chapter.objects.filter(story=story).count()
#         at_threshold = story.contract_status != 'signed' and chapter_count >= threshold
#         # if story.contract_status == 'signed':
#         #     story.contract_eligible = False

#         # Ensure contract_eligible flag is in sync (catches pre-flag stories)
#         if at_threshold and not story.contract_eligible and story.contract_status == 'none':
#             Story.objects.filter(pk=story.pk).update(contract_eligible=True)
#             story.contract_eligible = True
#         story.contract_eligible = False    

#         if story.contract_eligible or at_threshold or story.contract_status in ('under_review', 'contract_sent'):
#             if story.contract_status in ('contract_sent', 'under_review'):
#                 msg = 'Contract already in progress. No new chapters can be added at this stage.'
#             elif story.contract_status == 'under_review':
#                 msg = 'Your contract application is under review. New chapters are locked until it is resolved.'
#             else:
#                 msg = (
#                     f'This story has reached {threshold} chapters. '
#                     'Go to My Books and tap "Apply for Contract" to proceed. '
#                     'New chapters are locked until your contract is signed.'
#                 )
#             raise ValidationError({'detail': msg})
#         chapter = serializer.save(story=story)
#         # if chapter.is_published:
#         #     notify_followers_new_chapter.delay(chapter.id)
#         if chapter.is_published:
#             try:
#                 notify_followers_new_chapter.delay(chapter.id)
#             except Exception:
#                 pass  # Don't crash if Redis/Celery is unavailable


# class ChapterDetailView(generics.RetrieveUpdateDestroyAPIView):
#     def get_serializer_class(self):
#         if self.request.method in ('PUT', 'PATCH'):
#             return ChapterCreateUpdateSerializer
#         return ChapterDetailSerializer

#     def get_queryset(self):
#         story = get_object_or_404(Story, slug=self.kwargs['story_slug'])
#         return Chapter.objects.filter(story=story)

#     def get_object(self):
#         chapter = get_object_or_404(
#             Chapter,
#             story__slug=self.kwargs['story_slug'],
#             chapter_number=self.kwargs['chapter_number']
#         )
#         return chapter

#     def retrieve(self, request, *args, **kwargs):
#         chapter = self.get_object()
#         if request.user != chapter.story.author:
#             Chapter.objects.filter(pk=chapter.pk).update(views=F('views') + 1)
#         # Add XP for reading
#         if request.user.is_authenticated:
#             print(f"Adding XP for user {request.user.username} for reading chapter {chapter.id}")
#             request.user.add_reading_xp(10)
#             request.user.total_chapters_read = F('total_chapters_read') + 1
#             request.user.save(update_fields=['total_chapters_read'])
#         serializer = self.get_serializer(chapter)
#         return Response(serializer.data)


# class UnlockChapterView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, story_slug, chapter_number):
#         story   = get_object_or_404(Story, slug=story_slug)
#         chapter = get_object_or_404(Chapter, story=story, chapter_number=chapter_number)

#         if not chapter.is_locked:
#             return Response({'detail': 'Chapter is free.'}, status=200)

#         if story.author == request.user:
#             return Response({'detail': 'You own this story.'}, status=200)

#         # Check already unlocked
#         if ChapterUnlock.objects.filter(user=request.user, chapter=chapter).exists():
#             return Response({'detail': 'Already unlocked.'}, status=200)

#         # Check daily free chapter
#         today = timezone.now().date()
#         free_today = FreeChapterSchedule.objects.filter(
#             user=request.user, story=story, date=today
#         ).exists()

#         coins_needed = 0 if free_today else chapter.coin_cost

#         if coins_needed > 0:
#             if not request.user.deduct_coins(coins_needed, reason=f'Unlock Ch.{chapter_number} of {story.title}'):
#                 return Response({'detail': 'Insufficient coins.'}, status=402)
#             # Pay author
#             author_cut = int(coins_needed * 0.50)
#             story.author.add_coins(author_cut, reason=f'Chapter unlock revenue')

#         ChapterUnlock.objects.create(
#             user=request.user, chapter=chapter, coins_spent=coins_needed
#         )
#         Chapter.objects.filter(pk=chapter.pk).update(unlocks=F('unlocks') + 1)
#         # Chapter.objects.filter(pk=chapter.pk).update(is_unlocks=True)
#         Story.objects.filter(pk=story.pk).update(total_unlocks=F('total_unlocks') + 1)

#         return Response({'detail': 'Chapter unlocked.', 'coins_spent': coins_needed}, status=200)

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import F
from django.utils import timezone
from .models import Chapter, ChapterUnlock, FreeChapterSchedule
from .serializers import ChapterListSerializer, ChapterDetailSerializer, ChapterCreateUpdateSerializer
from apps.stories.models import Story
from apps.users.permissions import IsAuthorOrReadOnly
from apps.notifications.tasks import notify_followers_new_chapter


class ChapterListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return ChapterCreateUpdateSerializer if self.request.method == 'POST' else ChapterListSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.request.method == 'POST' else [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        self._story_contract_eligible = False
        response = super().create(request, *args, **kwargs)
        if self._story_contract_eligible:
            response.data['contract_eligible'] = True
        return response

    def get_queryset(self):
        story = get_object_or_404(Story, slug=self.kwargs['story_slug'])
        qs    = Chapter.objects.filter(story=story, is_published=True)
        if self.request.user.is_authenticated and story.author == self.request.user:
            qs = Chapter.objects.filter(story=story)
        order = self.request.query_params.get('order', 'asc')
        ordering = '-chapter_number' if order == 'desc' else 'chapter_number'
        return qs.order_by(ordering)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied, ValidationError
        story = get_object_or_404(Story, slug=self.kwargs['story_slug'])
        if story.author != self.request.user:
            raise PermissionDenied
        # Block new chapters once the story hits threshold or author has applied
        from apps.stories.models import PlatformSettings
        threshold = (
            story.review_threshold_override
            if story.review_threshold_override
            else PlatformSettings.get_threshold()
        )
        # Signed authors can always write new chapters — skip all threshold checks.
        if story.contract_status == 'signed':
            chapter = serializer.save(story=story)
            if chapter.is_published:
                try:
                    notify_followers_new_chapter.delay(chapter.id)
                except Exception:
                    pass
            return

        chapter_count = Chapter.objects.filter(story=story).count()
        at_threshold = chapter_count >= threshold

        # Ensure contract_eligible flag is in sync (catches pre-flag stories)
        if at_threshold and not story.contract_eligible and story.contract_status == 'none':
            Story.objects.filter(pk=story.pk).update(contract_eligible=True)
            story.contract_eligible = True

        if story.contract_eligible or at_threshold or story.contract_status in ('under_review', 'contract_sent', 'awaiting_signature', 'rejected'):
            if story.contract_status == 'awaiting_signature':
                msg = 'Your contract is ready to sign — new chapters are locked until you sign.'
            elif story.contract_status == 'contract_sent':
                msg = 'Your story is under CE review — new chapters are locked until your contract is signed.'
            elif story.contract_status == 'under_review':
                msg = 'Your contract application is under review. New chapters are locked until it is resolved.'
            elif story.contract_status == 'rejected':
                msg = 'Your contract application has been rejected. New chapters are locked until you address the feedback.'
            else:
                msg = (
                    f'This story has reached {threshold} chapters. '
                    'Go to My Books and tap "Apply for Contract" to proceed. '
                    'New chapters are locked until your contract is signed.'
                )
            raise ValidationError({'detail': msg})
        chapter = serializer.save(story=story)
        if chapter.is_published:
            try:
                notify_followers_new_chapter.delay(chapter.id)
            except Exception:
                pass  # Don't crash if Redis/Celery is unavailable
        # Refresh story from DB so contract_eligible reflects _check_editorial_trigger's update.
        story.refresh_from_db(fields=['contract_eligible', 'contract_status'])
        self._story_contract_eligible = story.contract_eligible and story.contract_status == 'none'


class ChapterDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ChapterCreateUpdateSerializer
        return ChapterDetailSerializer

    def perform_update(self, serializer):
        data = serializer.validated_data
        if data.get('status') == Chapter.STATUS_PUBLISHED or data.get('is_published') is True:
            data.pop('status', None)
            data.pop('is_published', None)
        chapter = serializer.save(**data)
        story = chapter.story
        story.refresh_from_db(fields=['contract_eligible', 'contract_status'])
        self._story_contract_eligible = story.contract_eligible and story.contract_status == 'none' and story.contract_status == 'none'

    def update(self, request, *args, **kwargs):
        self._story_contract_eligible = False
        chapter = self.get_object()

        # Intercept edits to published chapters — queue for SE review instead
        if chapter.status == Chapter.STATUS_PUBLISHED:
            return self._create_edit_request(request, chapter)

        response = super().update(request, *args, **kwargs)
        if self._story_contract_eligible:
            response.data['contract_eligible'] = True
        return response

    def _create_edit_request(self, request, chapter):
        from .models import ChapterEditRequest
        from rest_framework.response import Response

        new_content = request.data.get('content', '').strip()
        new_title   = request.data.get('title', '').strip()

        if not new_content:
            return Response({'detail': 'content is required.'}, status=400)

        # Upsert: update the existing pending request or create a new one
        edit_req, _ = ChapterEditRequest.objects.update_or_create(
            chapter=chapter,
            author=request.user,
            status=ChapterEditRequest.STATUS_PENDING,
            defaults={
                'pending_title':   new_title or chapter.title,
                'pending_content': new_content,
            },
        )

        # Notify the author's assigned SE
        try:
            from apps.editorial.models import AuthorEditorLink
            from apps.notifications.services import create_notification
            link = AuthorEditorLink.objects.filter(
                author=request.user
            ).select_related('editor').first()
            if link:
                create_notification(
                    link.editor,
                    'chapter_edit_review',
                    f'{request.user.username} submitted an edit for '
                    f'"{chapter.story.title}" Ch.{chapter.chapter_number} — review required.',
                )
        except Exception:
            pass

        return Response({
            'ok':     True,
            'status': 'in_review',
            'detail': 'Your edit has been submitted for SE review. It will go live once approved.',
            'edit_request_id': edit_req.pk,
        }, status=202)

    def get_queryset(self):
        story = get_object_or_404(Story, slug=self.kwargs['story_slug'])
        return Chapter.objects.filter(story=story)

    def get_object(self):
        chapter = get_object_or_404(
            Chapter,
            story__slug=self.kwargs['story_slug'],
            chapter_number=self.kwargs['chapter_number']
        )
        return chapter

    def retrieve(self, request, *args, **kwargs):
        chapter = self.get_object()
        if request.user != chapter.story.author:
            Chapter.objects.filter(pk=chapter.pk).update(views=F('views') + 1)
        # Add XP for reading
        if request.user.is_authenticated:
            print(f"Adding XP for user {request.user.username} for reading chapter {chapter.id}")
            request.user.add_reading_xp(10)
            request.user.total_chapters_read = F('total_chapters_read') + 1
            request.user.save(update_fields=['total_chapters_read'])
        serializer = self.get_serializer(chapter)
        return Response(serializer.data)


class DownloadStoryView(APIView):
    """POST /api/chapters/<story_slug>/chapters/download/

    Returns every published chapter with FULL content for offline reading.
    The app gates this behind a rewarded ad (method='ad') or a coin charge
    (method='coins'); VIP subscribers pay nothing.
    """
    permission_classes = [permissions.IsAuthenticated]
    COIN_COST = 120

    def post(self, request, story_slug):
        story = get_object_or_404(Story, slug=story_slug)
        method = (request.data.get('method') or '').lower()

        # Exclusive stories: offline download is a VIP perk — no ad/coin path
        if story.is_exclusive and not getattr(request.user, 'is_vip', False):
            return Response(
                {'detail': 'This story is exclusive — offline download '
                           'requires a VIP subscription.'},
                status=403,
            )

        coins_spent = 0
        if getattr(request.user, 'is_vip', False):
            pass  # included with the VIP subscription
        elif method == 'coins':
            if not request.user.deduct_coins(
                    self.COIN_COST, reason=f'Offline download: {story.title}'):
                return Response({'detail': 'Insufficient coins.'}, status=402)
            coins_spent = self.COIN_COST
        elif method != 'ad':
            return Response(
                {'detail': "method must be 'ad' or 'coins'"}, status=400)

        chapters = Chapter.objects.filter(
            story=story, is_published=True).order_by('chapter_number')
        return Response({
            'story': story.title,
            'coins_spent': coins_spent,
            'chapters': [{
                'chapter_number': c.chapter_number,
                'title': c.title,
                'content': c.content,
            } for c in chapters],
        })


class UnlockChapterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, story_slug, chapter_number):
        story   = get_object_or_404(Story, slug=story_slug)
        chapter = get_object_or_404(Chapter, story=story, chapter_number=chapter_number)

        if not chapter.is_locked:
            return Response({'detail': 'Chapter is free.'}, status=200)

        if story.author == request.user:
            return Response({'detail': 'You own this story.'}, status=200)

        # VIP subscription includes every locked chapter — nothing to pay
        if getattr(request.user, 'is_vip', False):
            return Response({'detail': 'Included with your VIP subscription.',
                             'coins_spent': 0}, status=200)

        # Check already unlocked
        if ChapterUnlock.objects.filter(user=request.user, chapter=chapter).exists():
            return Response({'detail': 'Already unlocked.'}, status=200)

        # Check daily free chapter
        today = timezone.now().date()
        free_today = FreeChapterSchedule.objects.filter(
            user=request.user, story=story, date=today
        ).exists()

        coins_needed = 0 if free_today else chapter.coin_cost

        if coins_needed > 0:
            if not request.user.deduct_coins(coins_needed, reason=f'Unlock Ch.{chapter_number} of {story.title}'):
                return Response({'detail': 'Insufficient coins.'}, status=402)
            # Pay author
            author_cut = int(coins_needed * 0.30)
            story.author.add_coins(author_cut, reason=f'Chapter unlock revenue')

        ChapterUnlock.objects.create(
            user=request.user, chapter=chapter, coins_spent=coins_needed
        )
        Chapter.objects.filter(pk=chapter.pk).update(unlocks=F('unlocks') + 1)
        # Chapter.objects.filter(pk=chapter.pk).update(is_unlocks=True)
        Story.objects.filter(pk=story.pk).update(total_unlocks=F('total_unlocks') + 1)

        return Response({'detail': 'Chapter unlocked.', 'coins_spent': coins_needed}, status=200)


class PublishChapterView(APIView):
    """
    POST /api/<story_slug>/chapters/<chapter_number>/publish/
    Only the author can publish their own chapter.
    Only valid for contracted authors (contract_status='signed').
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, story_slug, chapter_number):
        story   = get_object_or_404(Story, slug=story_slug)
        chapter = get_object_or_404(Chapter, story=story, chapter_number=chapter_number)

        if story.author != request.user:
            return Response({'detail': 'Not your story.'}, status=403)

        if story.contract_status != 'signed':
            return Response(
                {'detail': 'Only contracted authors can publish chapters directly.'},
                status=403,
            )

        if chapter.is_published:
            return Response({'detail': 'Already published.'}, status=200)

        Chapter.objects.filter(pk=chapter.pk).update(
            status=Chapter.STATUS_PUBLISHED,
            is_published=True,
        )

        # Update story chapter count
        Story.objects.filter(pk=story.pk).update(
            total_chapters=Chapter.objects.filter(story=story).count()
        )

        # Notify followers
        try:
            notify_followers_new_chapter.delay(chapter.id)
        except Exception:
            pass

        return Response({'detail': 'Chapter published.', 'chapter_number': chapter_number})