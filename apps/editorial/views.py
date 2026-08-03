# # """
# # Editorial API Views
# # ===================

# # Two-tier editorial hierarchy: SE (Senior Editor) and CE (Chief Editor).

# # SE flow:
# #   - Authors link to SE via invite code
# #   - SE reviews chapters submitted by their linked authors
# #   - SE can approve, request revision, remove, or escalate to CE

# # CE flow:
# #   - Reviews SE-approved chapters and sends contracts
# #   - Manages SE team via invites
# # """

# # from datetime import timedelta
# # import logging

# # from django.shortcuts import get_object_or_404
# # from django.utils import timezone
# # from django.contrib.auth import get_user_model

# # from rest_framework import generics, permissions
# # from rest_framework.decorators import api_view, permission_classes, parser_classes
# # from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
# # from rest_framework.response import Response
# # from rest_framework.views import APIView

# # from apps.chapters.models import Chapter
# # from apps.users.models import AuthorProfile
# # from .models import EditorAssignment, AuthorEditorLink
# # from .serializers import (
# #     EditorAssignmentSerializer,
# #     AuthorEditorLinkSerializer,
# #     ChapterReviewListSerializer,
# #     ChapterReviewDetailSerializer,
# # )
# # from .permissions import IsSEOrAbove, IsCE, IsSE

# # User = get_user_model()


# # # ─── Story-level SE review ────────────────────────────────────────────────────

# # class SEStoryQueueView(generics.ListAPIView):
# #     """GET /api/editorial/story-queue/ — stories awaiting SE review."""
# #     permission_classes = [IsSE]

# #     def get(self, request, *args, **kwargs):
# #         from apps.stories.models import Story
# #         from apps.editorial.models import ContractApplication

# #         stories = Story.objects.filter(
# #             contract_status='under_review',
# #             author__editor_link__assigned_se=request.user,
# #         ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

# #         data = []
# #         for s in stories:
# #             chapters = list(
# #                 s.chapters.order_by('chapter_number').values(
# #                     'id', 'chapter_number', 'title', 'status',
# #                     'word_count', 'created_at', 'se_note',
# #                 )
# #             )
# #             try:
# #                 app = s.contract_application
# #                 app_status = app.status
# #                 app_id = app.id
# #                 se_note = app.se_note
# #             except ContractApplication.DoesNotExist:
# #                 app_status = 'pending'
# #                 app_id = None
# #                 se_note = ''

# #             data.append({
# #                 'id':              s.id,
# #                 'slug':            s.slug,
# #                 'title':           s.title,
# #                 'description':     s.description,
# #                 'cover_image':     s.cover_image.url if s.cover_image else '',
# #                 'status':          s.status,
# #                 'contract_status': s.contract_status,
# #                 'word_count':      s.word_count,
# #                 'total_chapters':  s.chapters.count(),
# #                 'author': {
# #                     'id':           s.author.id,
# #                     'username':     s.author.username,
# #                     'display_name': s.author.get_full_name() or s.author.username,
# #                     'email':        s.author.email,
# #                 },
# #                 'application': {
# #                     'id':     app_id,
# #                     'status': app_status,
# #                     'note':   se_note,
# #                 },
# #                 'chapters': chapters,
# #                 'submitted_at': s.updated_at,
# #             })

# #         return Response({'count': len(data), 'results': data})


# # class SEStoryDetailView(APIView):
# #     """GET /api/editorial/story-queue/<slug>/ — full story detail for SE review."""
# #     permission_classes = [IsSE]

# #     def get(self, request, slug):
# #         from apps.stories.models import Story
# #         from apps.editorial.models import ContractApplication

# #         story = get_object_or_404(
# #             Story,
# #             slug=slug,
# #             author__editor_link__assigned_se=request.user,
# #         )

# #         chapters = list(
# #             story.chapters.order_by('chapter_number').values(
# #                 'id', 'chapter_number', 'title', 'status',
# #                 'word_count', 'created_at', 'se_note', 'content',
# #             )
# #         )

# #         try:
# #             app = story.contract_application
# #             application = {
# #                 'id': app.id, 'status': app.status,
# #                 'note': app.se_note, 'applied_at': app.applied_at,
# #             }
# #         except ContractApplication.DoesNotExist:
# #             application = None

# #         return Response({
# #             'id':              story.id,
# #             'slug':            story.slug,
# #             'title':           story.title,
# #             'description':     story.description,
# #             'cover_image':     story.cover_image.url if story.cover_image else '',
# #             'status':          story.status,
# #             'contract_status': story.contract_status,
# #             'word_count':      story.word_count,
# #             'total_chapters':  story.chapters.count(),
# #             'author': {
# #                 'id':           story.author.id,
# #                 'username':     story.author.username,
# #                 'display_name': story.author.get_full_name() or story.author.username,
# #                 'email':        story.author.email,
# #             },
# #             'application': application,
# #             'chapters':    chapters,
# #         })


# # @api_view(['POST'])
# # @permission_classes([IsSE])
# # def se_approve_story(request, slug):
# #     """POST /api/editorial/story-queue/<slug>/approve/ — SE approves full story for CE."""
# #     from apps.stories.models import Story
# #     from apps.editorial.models import ContractApplication

# #     story = get_object_or_404(
# #         Story, slug=slug,
# #         author__editor_link__assigned_se=request.user,
# #         contract_status='under_review',
# #     )
# #     note = request.data.get('note', '')

# #     # Approve all pending chapters on this story
# #     Chapter.objects.filter(
# #         story=story,
# #         status__in=[
# #             Chapter.STATUS_PENDING_REVIEW,
# #             Chapter.STATUS_SE_REVIEWING,
# #         ],
# #     ).update(
# #         status=Chapter.STATUS_SE_APPROVED,
# #         reviewed_by_se=request.user,
# #         reviewed_at=timezone.now(),
# #     )

# #     # Advance the contract application
# #     try:
# #         app = story.contract_application
# #         app.status = ContractApplication.STATUS_SE_APPROVED
# #         app.se_note = note
# #         app.se_reviewed_at = timezone.now()
# #         app.assigned_se = request.user
# #         app.save(update_fields=['status', 'se_note', 'se_reviewed_at', 'assigned_se'])
# #     except ContractApplication.DoesNotExist:
# #         ContractApplication.objects.create(
# #             story=story, author=story.author, assigned_se=request.user,
# #             status=ContractApplication.STATUS_SE_APPROVED,
# #             se_note=note, se_reviewed_at=timezone.now(),
# #         )

# #     # Move story to contract_sent stage (now visible to CE)
# #     story.contract_status = 'contract_sent'
# #     story.save(update_fields=['contract_status'])

# #     # Notify author
# #     try:
# #         from apps.notifications.services import notify_user
# #         notify_user(
# #             story.author,
# #             title='Your story has been approved! 🎉',
# #             body=f'"{story.title}" has been approved by your editor and sent to the Chief Editor.',
# #             data={'screen': 'my_books', 'slug': story.slug},
# #         )
# #     except Exception:
# #         pass

# #     return Response({'status': 'approved', 'story': story.slug})


# # @api_view(['POST'])
# # @permission_classes([IsSE])
# # def se_reject_story(request, slug):
# #     """POST /api/editorial/story-queue/<slug>/reject/ — SE rejects / requests revision."""
# #     from apps.stories.models import Story
# #     from apps.editorial.models import ContractApplication

# #     story = get_object_or_404(
# #         Story, slug=slug,
# #         author__editor_link__assigned_se=request.user,
# #         contract_status='under_review',
# #     )
# #     reason = request.data.get('reason', '')
# #     action = request.data.get('action', 'revision')  # 'revision' or 'reject'

# #     if action == 'reject':
# #         new_contract = 'none'
# #         new_ch_status = Chapter.STATUS_REJECTED
# #         app_status = ContractApplication.STATUS_REJECTED
# #     else:
# #         new_contract = 'under_review'
# #         new_ch_status = Chapter.STATUS_SE_REVISION
# #         app_status = ContractApplication.STATUS_SE_REVIEW

# #     Chapter.objects.filter(
# #         story=story,
# #         status__in=[Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING],
# #     ).update(
# #         status=new_ch_status,
# #         se_note=reason,
# #         reviewed_by_se=request.user,
# #         reviewed_at=timezone.now(),
# #     )

# #     try:
# #         app = story.contract_application
# #         app.status = app_status
# #         app.se_note = reason
# #         app.se_reviewed_at = timezone.now()
# #         app.save(update_fields=['status', 'se_note', 'se_reviewed_at'])
# #     except ContractApplication.DoesNotExist:
# #         pass

# #     if action == 'reject':
# #         story.contract_status = 'none'
# #         story.save(update_fields=['contract_status'])

# #     try:
# #         from apps.notifications.services import notify_user
# #         msg = f'Your editor has requested revisions on "{story.title}".' if action == 'revision' else f'"{story.title}" was not approved at this time.'
# #         notify_user(story.author, title='Editor feedback on your story', body=msg,
# #                     data={'screen': 'my_books', 'slug': story.slug})
# #     except Exception:
# #         pass

# #     return Response({'status': action, 'story': story.slug})


# # @api_view(['POST'])
# # @permission_classes([IsSE])
# # def se_escalate_story_to_ce(request, slug):
# #     """POST /api/editorial/story-queue/<slug>/escalate/ — SE escalates story directly to CE."""
# #     from apps.stories.models import Story
# #     from apps.editorial.models import ContractApplication

# #     story = get_object_or_404(
# #         Story, slug=slug,
# #         author__editor_link__assigned_se=request.user,
# #     )
# #     reasoning = request.data.get('reasoning', '')

# #     story.contract_status = 'contract_sent'
# #     story.save(update_fields=['contract_status'])

# #     try:
# #         app = story.contract_application
# #         app.status = ContractApplication.STATUS_SE_APPROVED
# #         app.se_note = f'CE Escalation: {reasoning}'
# #         app.se_reviewed_at = timezone.now()
# #         app.save(update_fields=['status', 'se_note', 'se_reviewed_at'])
# #     except ContractApplication.DoesNotExist:
# #         pass

# #     return Response({'status': 'escalated_to_ce', 'story': story.slug})



# # class EditorialQueueView(generics.ListAPIView):
# #     """GET /api/editorial/queue/ — list chapters awaiting editorial review."""
# #     serializer_class = ChapterReviewListSerializer
# #     permission_classes = [IsSEOrAbove]

# #     def get_queryset(self):
# #         user = self.request.user
# #         if user.role == 'ce':
# #             return Chapter.objects.filter(status=Chapter.STATUS_SE_APPROVED)

# #         if user.role == 'se':
# #             return Chapter.objects.filter(
# #                 story__author__editor_link__assigned_se=user,
# #                 status__in=[Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING],
# #             )

# #         return Chapter.objects.none()


# # class EditorialChapterDetailView(generics.RetrieveAPIView):
# #     """GET /api/editorial/reviews/<id>/"""
# #     serializer_class = ChapterReviewDetailSerializer
# #     permission_classes = [IsSEOrAbove]
# #     queryset = Chapter.objects.all()


# # @api_view(['POST'])
# # @permission_classes([IsSEOrAbove])
# # def se_approve(request, pk):
# #     """POST /api/editorial/reviews/<id>/approve/"""
# #     chapter = get_object_or_404(Chapter, pk=pk)
# #     if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING]:
# #         return Response(
# #             {'detail': 'Chapter is not eligible for SE approval.'},
# #             status=400,
# #         )
# #     chapter.status = Chapter.STATUS_SE_APPROVED
# #     chapter.reviewed_by_se = request.user
# #     chapter.reviewed_at = timezone.now()
# #     chapter.save(update_fields=['status', 'reviewed_by_se', 'reviewed_at'])
# #     return Response({'status': 'se_approved', 'chapter_id': chapter.id})


# # @api_view(['POST'])
# # @permission_classes([IsSEOrAbove])
# # def se_request_revision(request, pk):
# #     """POST /api/editorial/reviews/<id>/request-revision/"""
# #     chapter = get_object_or_404(Chapter, pk=pk)
# #     if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING]:
# #         return Response(
# #             {'detail': 'Chapter is not currently in SE review.'},
# #             status=400,
# #         )
# #     message = request.data.get('message', '')
# #     chapter.status = Chapter.STATUS_SE_REVISION
# #     chapter.se_note = message
# #     chapter.reviewed_by_se = request.user
# #     chapter.reviewed_at = timezone.now()
# #     chapter.save(update_fields=['status', 'se_note', 'reviewed_by_se', 'reviewed_at'])
# #     return Response({'status': 'se_revision_requested', 'chapter_id': chapter.id})


# # @api_view(['POST'])
# # @permission_classes([IsSEOrAbove])
# # def se_remove_content(request, pk):
# #     """POST /api/editorial/reviews/<id>/remove/ — SE removes content from platform."""
# #     chapter = get_object_or_404(Chapter, pk=pk)
# #     if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING, Chapter.STATUS_SE_REVISION]:
# #         return Response(
# #             {'detail': 'Chapter is not eligible for removal.'},
# #             status=400,
# #         )
# #     reason = request.data.get('reason', '')
# #     chapter.status = Chapter.STATUS_REJECTED
# #     chapter.se_note = f'Removed: {reason}' if reason else 'Removed by SE'
# #     chapter.reviewed_by_se = request.user
# #     chapter.reviewed_at = timezone.now()
# #     chapter.save(update_fields=['status', 'se_note', 'reviewed_by_se', 'reviewed_at'])
# #     return Response({'status': 'removed', 'chapter_id': chapter.id})


# # @api_view(['POST'])
# # @permission_classes([IsSEOrAbove])
# # def se_escalate_to_ce(request, pk):
# #     """POST /api/editorial/reviews/<id>/escalate-to-ce/ — SE escalates to Chief Editor."""
# #     chapter = get_object_or_404(Chapter, pk=pk)
# #     if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING]:
# #         return Response(
# #             {'detail': 'Chapter is not eligible for CE escalation.'},
# #             status=400,
# #         )
# #     reasoning = request.data.get('reasoning', '')
# #     chapter.status = Chapter.STATUS_SE_APPROVED
# #     chapter.se_note = f'CE Escalation: {reasoning}' if reasoning else 'Escalated to CE by SE'
# #     chapter.reviewed_by_se = request.user
# #     chapter.reviewed_at = timezone.now()
# #     chapter.save(update_fields=['status', 'se_note', 'reviewed_by_se', 'reviewed_at'])
# #     return Response({'status': 'escalated_to_ce', 'chapter_id': chapter.id})


# # # ─── CE Story Review ──────────────────────────────────────────────────────────

# # class CEStoryQueueView(APIView):
# #     """GET /api/editorial/ce-story-queue/ — SE-approved stories awaiting CE action."""
# #     permission_classes = [IsCE]

# #     def get(self, request):
# #         from apps.stories.models import Story
# #         from apps.editorial.models import ContractApplication

# #         stories = Story.objects.filter(
# #             contract_status='contract_sent',
# #         ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

# #         data = []
# #         for s in stories:
# #             chapters = list(
# #                 s.chapters.order_by('chapter_number').values(
# #                     'id', 'chapter_number', 'title', 'status', 'word_count', 'created_at',
# #                 )
# #             )
# #             try:
# #                 app = s.contract_application
# #                 app_data = {
# #                     'id': app.id, 'status': app.status,
# #                     'se_note': app.se_note,
# #                     'applied_at': app.applied_at,
# #                     'assigned_se': app.assigned_se.username if app.assigned_se else None,
# #                 }
# #             except ContractApplication.DoesNotExist:
# #                 app_data = None

# #             # Resolve which SE approved this story
# #             try:
# #                 se = s.author.editor_link.assigned_se
# #                 se_info = {'username': se.username, 'display_name': se.get_full_name() or se.username} if se else None
# #             except Exception:
# #                 se_info = None

# #             data.append({
# #                 'id':              s.id,
# #                 'slug':            s.slug,
# #                 'title':           s.title,
# #                 'description':     s.description,
# #                 'cover_image':     s.cover_image.url if s.cover_image else '',
# #                 'status':          s.status,
# #                 'contract_status': s.contract_status,
# #                 'word_count':      s.word_count,
# #                 'total_chapters':  s.chapters.count(),
# #                 'author': {
# #                     'id':           s.author.id,
# #                     'username':     s.author.username,
# #                     'display_name': s.author.get_full_name() or s.author.username,
# #                     'email':        s.author.email,
# #                 },
# #                 'approved_by_se': se_info,
# #                 'application':    app_data,
# #                 'chapters':       chapters,
# #             })

# #         return Response({'count': len(data), 'results': data})


# # class CEStoryDetailView(APIView):
# #     """GET /api/editorial/ce-story-queue/<slug>/ — full story detail for CE."""
# #     permission_classes = [IsCE]

# #     def get(self, request, slug):
# #         from apps.stories.models import Story
# #         from apps.editorial.models import ContractApplication

# #         story = get_object_or_404(Story, slug=slug)

# #         chapters = list(
# #             story.chapters.order_by('chapter_number').values(
# #                 'id', 'chapter_number', 'title', 'status',
# #                 'word_count', 'created_at', 'se_note', 'content',
# #             )
# #         )

# #         try:
# #             app = story.contract_application
# #             application = {
# #                 'id': app.id, 'status': app.status, 'se_note': app.se_note,
# #                 'applied_at': app.applied_at, 'se_reviewed_at': app.se_reviewed_at,
# #                 'assigned_se': app.assigned_se.username if app.assigned_se else None,
# #             }
# #         except ContractApplication.DoesNotExist:
# #             application = None

# #         try:
# #             se = story.author.editor_link.assigned_se
# #             se_info = {'username': se.username, 'display_name': se.get_full_name() or se.username} if se else None
# #         except Exception:
# #             se_info = None

# #         return Response({
# #             'id':              story.id,
# #             'slug':            story.slug,
# #             'title':           story.title,
# #             'description':     story.description,
# #             'cover_image':     story.cover_image.url if story.cover_image else '',
# #             'status':          story.status,
# #             'contract_status': story.contract_status,
# #             'word_count':      story.word_count,
# #             'total_chapters':  story.chapters.count(),
# #             'author': {
# #                 'id':           story.author.id,
# #                 'username':     story.author.username,
# #                 'display_name': story.author.get_full_name() or story.author.username,
# #                 'email':        story.author.email,
# #             },
# #             'approved_by_se': se_info,
# #             'application':    application,
# #             'chapters':       chapters,
# #         })


# # @api_view(['POST'])
# # @permission_classes([IsCE])
# # def ce_send_contract_story(request, slug):
# #     """POST /api/editorial/ce-story-queue/<slug>/send-contract/ — CE sends contract to author."""
# #     from apps.stories.models import Story
# #     from apps.editorial.models import ContractApplication

# #     story = get_object_or_404(Story, slug=slug, contract_status='contract_sent')

# #     contract_type = request.data.get('contract_type', 'non_exclusive')
# #     ce_note = request.data.get('note', '')

# #     try:
# #         app = story.contract_application
# #         app.status = ContractApplication.STATUS_CONTRACT_SENT
# #         app.contract_sent_at = timezone.now()
# #         app.se_note = (app.se_note + '\nCE note: ' + ce_note).strip() if ce_note else app.se_note
# #         app.contract_type = contract_type
# #         app.save(update_fields=['status', 'contract_sent_at', 'se_note', 'contract_type'])
# #     except ContractApplication.DoesNotExist:
# #         ContractApplication.objects.create(
# #             story=story, author=story.author,
# #             status=ContractApplication.STATUS_CONTRACT_SENT,
# #             contract_sent_at=timezone.now(),
# #             contract_type=contract_type,
# #         )

# #     try:
# #         from apps.notifications.services import notify_user
# #         notify_user(
# #             story.author,
# #             title='Contract ready to sign! 📝',
# #             body=f'A contract for "{story.title}" has been sent to you. Open Novelux to review and sign.',
# #             data={'screen': 'my_books', 'slug': story.slug, 'action': 'sign_contract'},
# #         )
# #     except Exception:
# #         pass

# #     # ── Send contract email to the author ─────────────────────────────────
# #     try:
# #         from django.core.mail import send_mail
# #         from django.conf import settings as _settings
# #         author         = story.author
# #         platform       = 'Novelux'
# #         contract_label = 'Exclusive' if contract_type == 'exclusive' else 'Non-Exclusive'
# #         sign_url       = f'https://novelux.app/my-books/{story.slug}/contract/'
# #         subject        = f'Your {platform} contract offer — "{story.title}"'
# #         text_body      = (
# #             f'Hi {author.first_name or author.username},\n\n'
# #             f'Congratulations! The Chief Editor has reviewed "{story.title}" and is offering you a {contract_label} contract.\n\n'
# #             f'Log in to Novelux to review and sign:\n{sign_url}\n\n'
# #             + (f'CE note: {ce_note}\n\n' if ce_note else '')
# #             + f'– The {platform} Editorial Team'
# #         )
# #         send_mail(
# #             subject=subject, message=text_body,
# #             from_email=_settings.DEFAULT_FROM_EMAIL,
# #             recipient_list=[author.email],
# #             fail_silently=True,
# #         )
# #     except Exception as _email_err:
# #         import logging
# #         logging.getLogger(__name__).error('Contract email error for %s: %s', story.slug, _email_err)

# #     # ── Push notification ───────────────────────────────────────────────
# #     try:
# #         from apps.notifications.services import notify_user
# #         notify_user(
# #             story.author,
# #             title='Contract ready to sign! 📝',
# #             body=f'A contract for "{story.title}" has been sent to your email. Open Novelux to review and sign.',
# #             data={'screen': 'my_books', 'slug': story.slug, 'action': 'sign_contract'},
# #         )
# #     except Exception:
# #         pass

# #     # Advance story status so it no longer appears in the CE pending queue on reload
# #     story.contract_status = 'awaiting_signature'
# #     story.save(update_fields=['contract_status'])

# #     return Response({'status': 'contract_sent', 'story': story.slug})


# # @api_view(['POST'])
# # @permission_classes([IsCE])
# # def ce_reject_story(request, slug):
# #     """POST /api/editorial/ce-story-queue/<slug>/reject/ — CE rejects or sends back to SE."""
# #     from apps.stories.models import Story
# #     from apps.editorial.models import ContractApplication

# #     story = get_object_or_404(Story, slug=slug)
# #     reason = request.data.get('reason', '')
# #     action = request.data.get('action', 'send_back')  # 'send_back' | 'reject'

# #     if action == 'reject':
# #         story.contract_status = 'none'
# #         story.save(update_fields=['contract_status'])
# #         try:
# #             app = story.contract_application
# #             app.status = ContractApplication.STATUS_REJECTED
# #             app.rejection_reason = reason
# #             app.rejected_at = timezone.now()
# #             app.save(update_fields=['status', 'rejection_reason', 'rejected_at'])
# #         except ContractApplication.DoesNotExist:
# #             pass
# #         notify_title = 'Contract not approved'
# #         notify_body  = f'"{story.title}" was not approved for a contract at this time.'
# #     else:
# #         # Send back to SE for re-review
# #         story.contract_status = 'under_review'
# #         story.save(update_fields=['contract_status'])
# #         try:
# #             app = story.contract_application
# #             app.status = ContractApplication.STATUS_SE_REVIEW
# #             app.se_note = f'CE returned for revision: {reason}'
# #             app.save(update_fields=['status', 'se_note'])
# #         except ContractApplication.DoesNotExist:
# #             pass
# #         notify_title = 'Story returned for revision'
# #         notify_body  = f'"{story.title}" has been returned by the Chief Editor for further revision.'

# #     try:
# #         from apps.notifications.services import notify_user
# #         notify_user(story.author, title=notify_title, body=notify_body,
# #                     data={'screen': 'my_books', 'slug': story.slug})
# #     except Exception:
# #         pass

# #     return Response({'status': action, 'story': story.slug})


# # @api_view(['POST'])
# # @permission_classes([IsCE])
# # def ce_edit_story_note(request, slug):
# #     """POST /api/editorial/ce-story-queue/<slug>/note/ — CE adds a note to a story application."""
# #     from apps.stories.models import Story
# #     from apps.editorial.models import ContractApplication

# #     story = get_object_or_404(Story, slug=slug)
# #     note = request.data.get('note', '').strip()

# #     try:
# #         app = story.contract_application
# #         app.se_note = note
# #         app.save(update_fields=['se_note'])
# #         return Response({'status': 'note_saved'})
# #     except ContractApplication.DoesNotExist:
# #         return Response({'detail': 'No contract application for this story.'}, status=404)



# # class CEEscalationsView(generics.ListAPIView):
# #     """GET /api/editorial/ce-escalations/ — chapters approved by SE and awaiting CE contract."""
# #     serializer_class = ChapterReviewListSerializer
# #     permission_classes = [IsCE]

# #     def get_queryset(self):
# #         return Chapter.objects.filter(status=Chapter.STATUS_SE_APPROVED)


# # @api_view(['POST'])
# # @permission_classes([IsCE])
# # def ce_send_contract(request, pk):
# #     """POST /api/editorial/reviews/<id>/ce-approve/ — send contract to author."""
# #     chapter = get_object_or_404(Chapter, pk=pk)
# #     if chapter.status != Chapter.STATUS_SE_APPROVED:
# #         return Response(
# #             {'detail': 'Only SE-approved chapters may be moved to contract stage.'},
# #             status=400,
# #         )
# #     chapter.status = Chapter.STATUS_CONTRACT_SENT
# #     chapter.save(update_fields=['status'])
# #     return Response({'status': 'contract_sent', 'chapter_id': chapter.id})


# # @api_view(['POST'])
# # @permission_classes([permissions.IsAuthenticated])
# # @parser_classes([MultiPartParser, FormParser, JSONParser])
# # def accept_contract(request):
# #     """POST /api/editorial/contracts/accept/ — author accepts a contract and publishes held chapters."""
# #     import logging
# #     logger = logging.getLogger(__name__)

# #     user = request.user
# #     if user.role != 'author':
# #         return Response({'detail': 'Only authors may accept contracts.'}, status=403)

# #     profile, _ = AuthorProfile.objects.get_or_create(user=user)
# #     if profile.has_contract:
# #         # Already signed — still ensure story/chapter statuses are correct
# #         from apps.stories.models import Story
# #         Story.objects.filter(author=user).exclude(
# #             status__in=['ongoing', 'completed', 'published']
# #         ).filter(contract_status__in=['contract_sent', 'awaiting_signature', 'under_review', 'signed']).update(
# #             contract_status='signed', status='ongoing'
# #         )
# #         published_count = Chapter.publish_held_chapters_for_author(user)
# #         return Response({'detail': 'Contract already accepted.', 'published_chapters': published_count}, status=200)

# #     contract_type = request.data.get('contract_type')
# #     if contract_type:
# #         valid_types = [choice[0] for choice in profile._meta.get_field('contract_type').choices]
# #         if contract_type not in valid_types:
# #             return Response({'detail': 'Invalid contract type.'}, status=400)
# #         profile.contract_type = contract_type

# #     profile.has_contract = True
# #     profile.contract_signed_at = timezone.now()
# #     profile.save(update_fields=['has_contract', 'contract_signed_at', 'contract_type'])

# #     # Mark all this author's stories in any pre-signed state → signed + ongoing
# #     from apps.stories.models import Story
# #     story_slug = request.data.get('slug', '').strip()
# #     updated = Story.objects.filter(
# #         author=user,
# #         contract_status__in=['contract_sent', 'awaiting_signature', 'under_review'],
# #     ).update(contract_status='signed', status='ongoing')
# #     logger.info('accept_contract: updated %d stories for user %s', updated, user.username)

# #     # If no stories matched above (edge case: status already moved), force the specific story
# #     if updated == 0 and story_slug:
# #         Story.objects.filter(author=user, slug=story_slug).update(
# #             contract_status='signed', status='ongoing'
# #         )
# #         logger.info('accept_contract: force-updated story %s', story_slug)

# #     # Mark ContractApplication as signed and save signature file
# #     if story_slug:
# #         try:
# #             story = Story.objects.get(slug=story_slug, author=user)
# #             app   = story.contract_application
# #             app.status    = app.STATUS_SIGNED
# #             app.signed_at = timezone.now()
# #             app.save(update_fields=['status', 'signed_at'])

# #             sig_file = request.FILES.get('signature')
# #             if sig_file:
# #                 from django.core.files.storage import default_storage
# #                 from django.core.files.base import ContentFile
# #                 default_storage.save(
# #                     f'signatures/{user.id}_{story_slug}.png',
# #                     ContentFile(sig_file.read()),
# #                 )
# #         except Exception as e:
# #             logger.warning('accept_contract: ContractApplication update failed: %s', e)

# #     published_count = Chapter.publish_held_chapters_for_author(user)
# #     logger.info('accept_contract: published %d chapters for user %s', published_count, user.username)
# #     return Response({
# #         'status': 'contract_accepted',
# #         'published_chapters': published_count,
# #     })


# # class EditorAssignmentListCreateView(generics.ListCreateAPIView):
# #     """GET/POST /api/editorial/assignments/"""
# #     serializer_class = EditorAssignmentSerializer
# #     permission_classes = [IsCE]
# #     queryset = EditorAssignment.objects.all().select_related('editor', 'supervisor')


# # class AuthorEditorLinkListCreateView(generics.ListCreateAPIView):
# #     """GET/POST /api/editorial/author-links/"""
# #     serializer_class = AuthorEditorLinkSerializer
# #     permission_classes = [IsCE]
# #     queryset = AuthorEditorLink.objects.all().select_related('author', 'assigned_se')


# # class EditorialTeamView(APIView):
# #     """GET /api/editorial/team/ — editorial org overview."""
# #     permission_classes = [IsCE]

# #     def get(self, request):
# #         data = {'ce': [], 'se': []}

# #         for ce in User.objects.filter(role='ce'):
# #             data['ce'].append({'id': ce.id, 'username': ce.username, 'email': ce.email})

# #         for se in User.objects.filter(role='se'):
# #             try:
# #                 ce_sup = se.editorial_assignment.supervisor
# #                 ce_name = ce_sup.username if ce_sup else None
# #             except Exception:
# #                 ce_name = None

# #             pending_count = Chapter.objects.filter(
# #                 story__author__editor_link__assigned_se=se,
# #                 status=Chapter.STATUS_PENDING_REVIEW,
# #             ).count()

# #             data['se'].append({
# #                 'id': se.id,
# #                 'username': se.username,
# #                 'email': se.email,
# #                 'reports_to_ce': ce_name,
# #                 'pending_count': pending_count,
# #                 'author_count': se.sourced_authors.count(),
# #                 'editor_code': se.editor_code or '',
# #             })

# #         return Response(data)


# # class EditorialStatsView(APIView):
# #     """GET /api/editorial/stats/ — role-aware editorial metrics."""
# #     permission_classes = [IsSEOrAbove]

# #     def get(self, request):
# #         user = request.user

# #         if user.role == 'se':
# #             return Response({
# #                 'pending_review_count': Chapter.objects.filter(
# #                     story__author__editor_link__assigned_se=user,
# #                     status=Chapter.STATUS_PENDING_REVIEW,
# #                 ).count(),
# #                 'approved_this_week': Chapter.objects.filter(
# #                     reviewed_by_se=user,
# #                     reviewed_at__gte=timezone.now() - timedelta(days=7),
# #                     status=Chapter.STATUS_SE_APPROVED,
# #                 ).count(),
# #                 'author_count': user.sourced_authors.count(),
# #             })

# #         if user.role == 'ce':
# #             return Response({
# #                 'contract_ready_count': Chapter.objects.filter(status=Chapter.STATUS_SE_APPROVED).count(),
# #                 'total_editors': User.objects.filter(role='se').count(),
# #                 'se_count': User.objects.filter(role='se').count(),
# #             })

# #         return Response({})


# # @api_view(['POST'])
# # @permission_classes([permissions.AllowAny])
# # def validate_editor_code(request):
# #     logger = logging.getLogger(__name__)
# #     logger.info(f'Validating editor code: {request.data}')
# #     code = request.data.get('code', '').strip().upper()
# #     if not code:
# #         return Response({'valid': False, 'error': 'Code is required.'}, status=400)

# #     try:
# #         editor = User.objects.get(editor_code=code, role='se')
# #         display = editor.get_full_name() or editor.username
# #         author_count = editor.sourced_authors.count()
# #         return Response({
# #             'valid': True,
# #             'editor_display_name': display,
# #             'editor_role': editor.role,
# #             'author_count': author_count,
# #         })
# #     except User.DoesNotExist:
# #         return Response({'valid': False, 'error': 'Invalid editor code.'})


# # @api_view(['POST'])
# # @permission_classes([permissions.IsAuthenticated])
# # def link_editor_by_code(request):
# #     user = request.user
# #     code = request.data.get('code', '').strip().upper()
# #     link, error = AuthorEditorLink.link_by_code(user, code)
# #     if error:
# #         return Response({'error': error}, status=400)
# #     from .serializers import AuthorEditorLinkSerializer
# #     return Response({
# #         'success': True,
# #         'link': AuthorEditorLinkSerializer(link).data,
# #     })


# # @api_view(['GET'])
# # @permission_classes([permissions.IsAuthenticated])
# # def my_editor_link(request):
# #     user = request.user
# #     try:
# #         link = AuthorEditorLink.objects.select_related('assigned_se').get(author=user)
# #         se = link.assigned_se
# #         return Response({
# #             'linked': True,
# #             'link_method': link.link_method,
# #             'assigned_at': link.assigned_at,
# #             'se': {
# #                 'display_name': se.get_full_name() or se.username if se else None,
# #                 'author_count': se.sourced_authors.count() if se else 0,
# #             } if se else None,
# #         })
# #     except AuthorEditorLink.DoesNotExist:
# #         return Response({'linked': False, 'se': None})


# # @api_view(['GET'])
# # @permission_classes([IsSE])
# # def my_editor_code(request):
# #     user = request.user
# #     code = user.editor_code or user.generate_editor_code()
# #     return Response({
# #         'editor_code': code,
# #         'author_count': user.sourced_authors.count(),
# #         'share_hint': f'Share this code with authors so they can link to you at signup: {code}',
# #     })




# """
# Editorial API Views
# ===================

# Two-tier editorial hierarchy: SE (Senior Editor) and CE (Chief Editor).

# SE flow:
#   - Authors link to SE via invite code
#   - SE reviews chapters submitted by their linked authors
#   - SE can approve, request revision, remove, or escalate to CE

# CE flow:
#   - Reviews SE-approved chapters and sends contracts
#   - Manages SE team via invites
# """

# from datetime import timedelta
# import logging

# from django.shortcuts import get_object_or_404
# from django.utils import timezone
# from django.contrib.auth import get_user_model

# from rest_framework import generics, permissions
# from rest_framework.decorators import api_view, permission_classes, parser_classes
# from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
# from rest_framework.response import Response
# from rest_framework.views import APIView

# from apps.chapters.models import Chapter
# from apps.users.models import AuthorProfile
# from .models import EditorAssignment, AuthorEditorLink
# from .serializers import (
#     EditorAssignmentSerializer,
#     AuthorEditorLinkSerializer,
#     ChapterReviewListSerializer,
#     ChapterReviewDetailSerializer,
# )
# from .permissions import IsSEOrAbove, IsCE, IsSE

# User = get_user_model()


# # ─── Story-level SE review ────────────────────────────────────────────────────

# class SEStoryQueueView(generics.ListAPIView):
#     """GET /api/editorial/story-queue/ — stories awaiting SE review."""
#     permission_classes = [IsSE]

#     def get(self, request, *args, **kwargs):
#         from apps.stories.models import Story
#         from apps.editorial.models import ContractApplication

#         stories = Story.objects.filter(
#             contract_status='under_review',
#             author__editor_link__assigned_se=request.user,
#         ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

#         data = []
#         for s in stories:
#             chapters = list(
#                 s.chapters.order_by('chapter_number').values(
#                     'id', 'chapter_number', 'title', 'status',
#                     'word_count', 'created_at', 'se_note',
#                 )
#             )
#             try:
#                 app = s.contract_application
#                 app_status = app.status
#                 app_id = app.id
#                 se_note = app.se_note
#             except ContractApplication.DoesNotExist:
#                 app_status = 'pending'
#                 app_id = None
#                 se_note = ''

#             data.append({
#                 'id':              s.id,
#                 'slug':            s.slug,
#                 'title':           s.title,
#                 'description':     s.description,
#                 'cover_image':     s.cover_image.url if s.cover_image else '',
#                 'status':          s.status,
#                 'contract_status': s.contract_status,
#                 'word_count':      s.word_count,
#                 'total_chapters':  s.chapters.count(),
#                 'author': {
#                     'id':           s.author.id,
#                     'username':     s.author.username,
#                     'display_name': s.author.get_full_name() or s.author.username,
#                     'email':        s.author.email,
#                 },
#                 'application': {
#                     'id':     app_id,
#                     'status': app_status,
#                     'note':   se_note,
#                 },
#                 'chapters': chapters,
#                 'submitted_at': s.updated_at,
#             })

#         return Response({'count': len(data), 'results': data})


# class SEStoryDetailView(APIView):
#     """GET /api/editorial/story-queue/<slug>/ — full story detail for SE review."""
#     permission_classes = [IsSE]

#     def get(self, request, slug):
#         from apps.stories.models import Story
#         from apps.editorial.models import ContractApplication

#         story = get_object_or_404(
#             Story,
#             slug=slug,
#             author__editor_link__assigned_se=request.user,
#         )

#         chapters = list(
#             story.chapters.order_by('chapter_number').values(
#                 'id', 'chapter_number', 'title', 'status',
#                 'word_count', 'created_at', 'se_note', 'content',
#             )
#         )

#         try:
#             app = story.contract_application
#             application = {
#                 'id': app.id, 'status': app.status,
#                 'note': app.se_note, 'applied_at': app.applied_at,
#             }
#         except ContractApplication.DoesNotExist:
#             application = None

#         return Response({
#             'id':              story.id,
#             'slug':            story.slug,
#             'title':           story.title,
#             'description':     story.description,
#             'cover_image':     story.cover_image.url if story.cover_image else '',
#             'status':          story.status,
#             'contract_status': story.contract_status,
#             'word_count':      story.word_count,
#             'total_chapters':  story.chapters.count(),
#             'author': {
#                 'id':           story.author.id,
#                 'username':     story.author.username,
#                 'display_name': story.author.get_full_name() or story.author.username,
#                 'email':        story.author.email,
#             },
#             'application': application,
#             'chapters':    chapters,
#         })


# @api_view(['POST'])
# @permission_classes([IsSE])
# def se_approve_story(request, slug):
#     """POST /api/editorial/story-queue/<slug>/approve/ — SE approves full story for CE."""
#     from apps.stories.models import Story
#     from apps.editorial.models import ContractApplication

#     story = get_object_or_404(
#         Story, slug=slug,
#         author__editor_link__assigned_se=request.user,
#         contract_status='under_review',
#     )
#     note = request.data.get('note', '')

#     # Approve all pending chapters on this story
#     Chapter.objects.filter(
#         story=story,
#         status__in=[
#             Chapter.STATUS_PENDING_REVIEW,
#             Chapter.STATUS_SE_REVIEWING,
#         ],
#     ).update(
#         status=Chapter.STATUS_SE_APPROVED,
#         reviewed_by_se=request.user,
#         reviewed_at=timezone.now(),
#     )

#     # Advance the contract application
#     try:
#         app = story.contract_application
#         app.status = ContractApplication.STATUS_SE_APPROVED
#         app.se_note = note
#         app.se_reviewed_at = timezone.now()
#         app.assigned_se = request.user
#         app.save(update_fields=['status', 'se_note', 'se_reviewed_at', 'assigned_se'])
#     except ContractApplication.DoesNotExist:
#         ContractApplication.objects.create(
#             story=story, author=story.author, assigned_se=request.user,
#             status=ContractApplication.STATUS_SE_APPROVED,
#             se_note=note, se_reviewed_at=timezone.now(),
#         )

#     # Move story to contract_sent stage (now visible to CE)
#     story.contract_status = 'contract_sent'
#     story.save(update_fields=['contract_status'])

#     # Notify author
#     try:
#         from apps.notifications.services import on_se_approved
#         on_se_approved(story.author, story)
#     except Exception:
#         pass

#     return Response({'status': 'approved', 'story': story.slug})


# @api_view(['POST'])
# @permission_classes([IsSE])
# def se_reject_story(request, slug):
#     """POST /api/editorial/story-queue/<slug>/reject/ — SE rejects / requests revision."""
#     from apps.stories.models import Story
#     from apps.editorial.models import ContractApplication

#     story = get_object_or_404(
#         Story, slug=slug,
#         author__editor_link__assigned_se=request.user,
#         contract_status='under_review',
#     )
#     reason = request.data.get('reason', '')
#     action = request.data.get('action', 'revision')  # 'revision' or 'reject'

#     if action == 'reject':
#         new_contract = 'none'
#         new_ch_status = Chapter.STATUS_REJECTED
#         app_status = ContractApplication.STATUS_REJECTED
#     else:
#         new_contract = 'under_review'
#         new_ch_status = Chapter.STATUS_SE_REVISION
#         app_status = ContractApplication.STATUS_SE_REVIEW

#     Chapter.objects.filter(
#         story=story,
#         status__in=[Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING],
#     ).update(
#         status=new_ch_status,
#         se_note=reason,
#         reviewed_by_se=request.user,
#         reviewed_at=timezone.now(),
#     )

#     try:
#         app = story.contract_application
#         app.status = app_status
#         app.se_note = reason
#         app.se_reviewed_at = timezone.now()
#         app.save(update_fields=['status', 'se_note', 'se_reviewed_at'])
#     except ContractApplication.DoesNotExist:
#         pass

#     if action == 'reject':
#         story.contract_status = 'none'
#         story.save(update_fields=['contract_status'])

#     try:
#         from apps.notifications.services import on_se_revision_requested, on_contract_rejected
#         from apps.notifications.models import Notification
#         from apps.notifications.services import create_notification
#         if action == 'revision':
#             on_se_revision_requested(story.author, story, note)
#         else:
#             on_contract_rejected(story.author, story, reason=note)
#     except Exception:
#         pass

#     return Response({'status': action, 'story': story.slug})


# @api_view(['POST'])
# @permission_classes([IsSE])
# def se_escalate_story_to_ce(request, slug):
#     """POST /api/editorial/story-queue/<slug>/escalate/ — SE escalates story directly to CE."""
#     from apps.stories.models import Story
#     from apps.editorial.models import ContractApplication

#     story = get_object_or_404(
#         Story, slug=slug,
#         author__editor_link__assigned_se=request.user,
#     )
#     reasoning = request.data.get('reasoning', '')

#     story.contract_status = 'contract_sent'
#     story.save(update_fields=['contract_status'])

#     try:
#         app = story.contract_application
#         app.status = ContractApplication.STATUS_SE_APPROVED
#         app.se_note = f'CE Escalation: {reasoning}'
#         app.se_reviewed_at = timezone.now()
#         app.save(update_fields=['status', 'se_note', 'se_reviewed_at'])
#     except ContractApplication.DoesNotExist:
#         pass

#     return Response({'status': 'escalated_to_ce', 'story': story.slug})



# class EditorialQueueView(generics.ListAPIView):
#     """GET /api/editorial/queue/ — list chapters awaiting editorial review."""
#     serializer_class = ChapterReviewListSerializer
#     permission_classes = [IsSEOrAbove]

#     def get_queryset(self):
#         user = self.request.user
#         if user.role == 'ce':
#             return Chapter.objects.filter(status=Chapter.STATUS_SE_APPROVED)

#         if user.role == 'se':
#             return Chapter.objects.filter(
#                 story__author__editor_link__assigned_se=user,
#                 status__in=[Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING],
#             )

#         return Chapter.objects.none()


# class EditorialChapterDetailView(generics.RetrieveAPIView):
#     """GET /api/editorial/reviews/<id>/"""
#     serializer_class = ChapterReviewDetailSerializer
#     permission_classes = [IsSEOrAbove]
#     queryset = Chapter.objects.all()


# @api_view(['POST'])
# @permission_classes([IsSEOrAbove])
# def se_approve(request, pk):
#     """POST /api/editorial/reviews/<id>/approve/"""
#     chapter = get_object_or_404(Chapter, pk=pk)
#     if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING]:
#         return Response(
#             {'detail': 'Chapter is not eligible for SE approval.'},
#             status=400,
#         )
#     chapter.status = Chapter.STATUS_SE_APPROVED
#     chapter.reviewed_by_se = request.user
#     chapter.reviewed_at = timezone.now()
#     chapter.save(update_fields=['status', 'reviewed_by_se', 'reviewed_at'])
#     return Response({'status': 'se_approved', 'chapter_id': chapter.id})


# @api_view(['POST'])
# @permission_classes([IsSEOrAbove])
# def se_request_revision(request, pk):
#     """POST /api/editorial/reviews/<id>/request-revision/"""
#     chapter = get_object_or_404(Chapter, pk=pk)
#     if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING]:
#         return Response(
#             {'detail': 'Chapter is not currently in SE review.'},
#             status=400,
#         )
#     message = request.data.get('message', '')
#     chapter.status = Chapter.STATUS_SE_REVISION
#     chapter.se_note = message
#     chapter.reviewed_by_se = request.user
#     chapter.reviewed_at = timezone.now()
#     chapter.save(update_fields=['status', 'se_note', 'reviewed_by_se', 'reviewed_at'])
#     return Response({'status': 'se_revision_requested', 'chapter_id': chapter.id})


# @api_view(['POST'])
# @permission_classes([IsSEOrAbove])
# def se_remove_content(request, pk):
#     """POST /api/editorial/reviews/<id>/remove/ — SE removes content from platform."""
#     chapter = get_object_or_404(Chapter, pk=pk)
#     if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING, Chapter.STATUS_SE_REVISION]:
#         return Response(
#             {'detail': 'Chapter is not eligible for removal.'},
#             status=400,
#         )
#     reason = request.data.get('reason', '')
#     chapter.status = Chapter.STATUS_REJECTED
#     chapter.se_note = f'Removed: {reason}' if reason else 'Removed by SE'
#     chapter.reviewed_by_se = request.user
#     chapter.reviewed_at = timezone.now()
#     chapter.save(update_fields=['status', 'se_note', 'reviewed_by_se', 'reviewed_at'])
#     return Response({'status': 'removed', 'chapter_id': chapter.id})


# @api_view(['POST'])
# @permission_classes([IsSEOrAbove])
# def se_escalate_to_ce(request, pk):
#     """POST /api/editorial/reviews/<id>/escalate-to-ce/ — SE escalates to Chief Editor."""
#     chapter = get_object_or_404(Chapter, pk=pk)
#     if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING]:
#         return Response(
#             {'detail': 'Chapter is not eligible for CE escalation.'},
#             status=400,
#         )
#     reasoning = request.data.get('reasoning', '')
#     chapter.status = Chapter.STATUS_SE_APPROVED
#     chapter.se_note = f'CE Escalation: {reasoning}' if reasoning else 'Escalated to CE by SE'
#     chapter.reviewed_by_se = request.user
#     chapter.reviewed_at = timezone.now()
#     chapter.save(update_fields=['status', 'se_note', 'reviewed_by_se', 'reviewed_at'])
#     return Response({'status': 'escalated_to_ce', 'chapter_id': chapter.id})


# # ─── CE Story Review ──────────────────────────────────────────────────────────

# class CEStoryQueueView(APIView):
#     """GET /api/editorial/ce-story-queue/ — SE-approved stories awaiting CE action."""
#     permission_classes = [IsCE]

#     def get(self, request):
#         from apps.stories.models import Story
#         from apps.editorial.models import ContractApplication

#         stories = Story.objects.filter(
#             contract_status='contract_sent',
#         ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

#         data = []
#         for s in stories:
#             chapters = list(
#                 s.chapters.order_by('chapter_number').values(
#                     'id', 'chapter_number', 'title', 'status', 'word_count', 'created_at',
#                 )
#             )
#             try:
#                 app = s.contract_application
#                 app_data = {
#                     'id': app.id, 'status': app.status,
#                     'se_note': app.se_note,
#                     'applied_at': app.applied_at,
#                     'assigned_se': app.assigned_se.username if app.assigned_se else None,
#                 }
#             except ContractApplication.DoesNotExist:
#                 app_data = None

#             # Resolve which SE approved this story
#             try:
#                 se = s.author.editor_link.assigned_se
#                 se_info = {'username': se.username, 'display_name': se.get_full_name() or se.username} if se else None
#             except Exception:
#                 se_info = None

#             data.append({
#                 'id':              s.id,
#                 'slug':            s.slug,
#                 'title':           s.title,
#                 'description':     s.description,
#                 'cover_image':     s.cover_image.url if s.cover_image else '',
#                 'status':          s.status,
#                 'contract_status': s.contract_status,
#                 'word_count':      s.word_count,
#                 'total_chapters':  s.chapters.count(),
#                 'author': {
#                     'id':           s.author.id,
#                     'username':     s.author.username,
#                     'display_name': s.author.get_full_name() or s.author.username,
#                     'email':        s.author.email,
#                 },
#                 'approved_by_se': se_info,
#                 'application':    app_data,
#                 'chapters':       chapters,
#             })

#         return Response({'count': len(data), 'results': data})


# class CEStoryDetailView(APIView):
#     """GET /api/editorial/ce-story-queue/<slug>/ — full story detail for CE."""
#     permission_classes = [IsCE]

#     def get(self, request, slug):
#         from apps.stories.models import Story
#         from apps.editorial.models import ContractApplication

#         story = get_object_or_404(Story, slug=slug)

#         chapters = list(
#             story.chapters.order_by('chapter_number').values(
#                 'id', 'chapter_number', 'title', 'status',
#                 'word_count', 'created_at', 'se_note', 'content',
#             )
#         )

#         try:
#             app = story.contract_application
#             application = {
#                 'id': app.id, 'status': app.status, 'se_note': app.se_note,
#                 'applied_at': app.applied_at, 'se_reviewed_at': app.se_reviewed_at,
#                 'assigned_se': app.assigned_se.username if app.assigned_se else None,
#             }
#         except ContractApplication.DoesNotExist:
#             application = None

#         try:
#             se = story.author.editor_link.assigned_se
#             se_info = {'username': se.username, 'display_name': se.get_full_name() or se.username} if se else None
#         except Exception:
#             se_info = None

#         return Response({
#             'id':              story.id,
#             'slug':            story.slug,
#             'title':           story.title,
#             'description':     story.description,
#             'cover_image':     story.cover_image.url if story.cover_image else '',
#             'status':          story.status,
#             'contract_status': story.contract_status,
#             'word_count':      story.word_count,
#             'total_chapters':  story.chapters.count(),
#             'author': {
#                 'id':           story.author.id,
#                 'username':     story.author.username,
#                 'display_name': story.author.get_full_name() or story.author.username,
#                 'email':        story.author.email,
#             },
#             'approved_by_se': se_info,
#             'application':    application,
#             'chapters':       chapters,
#         })


# @api_view(['POST'])
# @permission_classes([IsCE])
# def ce_send_contract_story(request, slug):
#     """POST /api/editorial/ce-story-queue/<slug>/send-contract/ — CE sends contract to author."""
#     from apps.stories.models import Story
#     from apps.editorial.models import ContractApplication

#     story = get_object_or_404(Story, slug=slug, contract_status='contract_sent')

#     contract_type = request.data.get('contract_type', 'non_exclusive')
#     ce_note = request.data.get('note', '')

#     try:
#         app = story.contract_application
#         app.status = ContractApplication.STATUS_CONTRACT_SENT
#         app.contract_sent_at = timezone.now()
#         app.se_note = (app.se_note + '\nCE note: ' + ce_note).strip() if ce_note else app.se_note
#         app.contract_type = contract_type
#         app.save(update_fields=['status', 'contract_sent_at', 'se_note', 'contract_type'])
#     except ContractApplication.DoesNotExist:
#         ContractApplication.objects.create(
#             story=story, author=story.author,
#             status=ContractApplication.STATUS_CONTRACT_SENT,
#             contract_sent_at=timezone.now(),
#             contract_type=contract_type,
#         )

#     # ── Send contract email to the author ─────────────────────────────────
#     try:
#         from django.core.mail import send_mail
#         from django.conf import settings as _settings
#         author         = story.author
#         platform       = 'Novelux'
#         contract_label = 'Exclusive' if contract_type == 'exclusive' else 'Non-Exclusive'
#         sign_url       = f'https://novelux-backend.com/my-books/{story.slug}/contract/'
#         subject        = f'Your {platform} contract offer — "{story.title}"'
#         text_body      = (
#             f'Hi {author.first_name or author.username},\n\n'
#             f'Congratulations! The Chief Editor has reviewed "{story.title}" and is offering you a {contract_label} contract.\n\n'
#             f'Log in to Novelux to review and sign:\n{sign_url}\n\n'
#             + (f'CE note: {ce_note}\n\n' if ce_note else '')
#             + f'– The {platform} Editorial Team'
#         )
#         send_mail(
#             subject=subject, message=text_body,
#             from_email=_settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[author.email],
#             fail_silently=True,
#         )
#     except Exception as _email_err:
#         import logging
#         logging.getLogger(__name__).error('Contract email error for %s: %s', story.slug, _email_err)

#     # ── In-app notification + push ──────────────────────────────────────
#     try:
#         from apps.notifications.services import on_contract_sent
#         on_contract_sent(story.author, story, contract_type)
#     except Exception:
#         pass

#     # Advance story status so it no longer appears in the CE pending queue on reload
#     story.contract_status = 'awaiting_signature'
#     story.save(update_fields=['contract_status'])

#     return Response({'status': 'contract_sent', 'story': story.slug})


# @api_view(['POST'])
# @permission_classes([IsCE])
# def ce_reject_story(request, slug):
#     """POST /api/editorial/ce-story-queue/<slug>/reject/ — CE rejects or sends back to SE."""
#     from apps.stories.models import Story
#     from apps.editorial.models import ContractApplication

#     story = get_object_or_404(Story, slug=slug)
#     reason = request.data.get('reason', '')
#     action = request.data.get('action', 'send_back')  # 'send_back' | 'reject'

#     if action == 'reject':
#         story.contract_status = 'none'
#         story.save(update_fields=['contract_status'])
#         try:
#             app = story.contract_application
#             app.status = ContractApplication.STATUS_REJECTED
#             app.rejection_reason = reason
#             app.rejected_at = timezone.now()
#             app.save(update_fields=['status', 'rejection_reason', 'rejected_at'])
#         except ContractApplication.DoesNotExist:
#             pass
#         notify_title = 'Contract not approved'
#         notify_body  = f'"{story.title}" was not approved for a contract at this time.'
#     else:
#         # Send back to SE for re-review
#         story.contract_status = 'under_review'
#         story.save(update_fields=['contract_status'])
#         try:
#             app = story.contract_application
#             app.status = ContractApplication.STATUS_SE_REVIEW
#             app.se_note = f'CE returned for revision: {reason}'
#             app.save(update_fields=['status', 'se_note'])
#         except ContractApplication.DoesNotExist:
#             pass
#         notify_title = 'Story returned for revision'
#         notify_body  = f'"{story.title}" has been returned by the Chief Editor for further revision.'

#     try:
#         from apps.notifications.services import create_notification
#         from apps.notifications.models import Notification
#         create_notification(
#             user=story.author,
#             notification_type=Notification.TYPE_SYSTEM,
#             title=notify_title,
#             message=notify_body,
#             data={'screen': 'my_books', 'slug': story.slug},
#         )
#     except Exception:
#         pass

#     return Response({'status': action, 'story': story.slug})


# @api_view(['POST'])
# @permission_classes([IsCE])
# def ce_edit_story_note(request, slug):
#     """POST /api/editorial/ce-story-queue/<slug>/note/ — CE adds a note to a story application."""
#     from apps.stories.models import Story
#     from apps.editorial.models import ContractApplication

#     story = get_object_or_404(Story, slug=slug)
#     note = request.data.get('note', '').strip()

#     try:
#         app = story.contract_application
#         app.se_note = note
#         app.save(update_fields=['se_note'])
#         return Response({'status': 'note_saved'})
#     except ContractApplication.DoesNotExist:
#         return Response({'detail': 'No contract application for this story.'}, status=404)



# class CEEscalationsView(generics.ListAPIView):
#     """GET /api/editorial/ce-escalations/ — chapters approved by SE and awaiting CE contract."""
#     serializer_class = ChapterReviewListSerializer
#     permission_classes = [IsCE]

#     def get_queryset(self):
#         return Chapter.objects.filter(status=Chapter.STATUS_SE_APPROVED)


# @api_view(['POST'])
# @permission_classes([IsCE])
# def ce_send_contract(request, pk):
#     """POST /api/editorial/reviews/<id>/ce-approve/ — send contract to author."""
#     chapter = get_object_or_404(Chapter, pk=pk)
#     if chapter.status != Chapter.STATUS_SE_APPROVED:
#         return Response(
#             {'detail': 'Only SE-approved chapters may be moved to contract stage.'},
#             status=400,
#         )
#     chapter.status = Chapter.STATUS_CONTRACT_SENT
#     chapter.save(update_fields=['status'])
#     return Response({'status': 'contract_sent', 'chapter_id': chapter.id})


# @api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])
# @parser_classes([MultiPartParser, FormParser, JSONParser])
# def accept_contract(request):
#     """POST /api/editorial/contracts/accept/ — author accepts a contract and publishes held chapters."""
#     import logging
#     logger = logging.getLogger(__name__)

#     user = request.user
#     if user.role != 'author':
#         return Response({'detail': 'Only authors may accept contracts.'}, status=403)

#     profile, _ = AuthorProfile.objects.get_or_create(user=user)
#     if profile.has_contract:
#         # Already signed — still ensure story/chapter statuses are correct
#         from apps.stories.models import Story
#         Story.objects.filter(author=user).exclude(
#             status__in=['ongoing', 'completed', 'published']
#         ).filter(contract_status__in=['contract_sent', 'awaiting_signature', 'under_review', 'signed']).update(
#             contract_status='signed', status='ongoing'
#         )
#         published_count = Chapter.publish_held_chapters_for_author(user)
#         return Response({'detail': 'Contract already accepted.', 'published_chapters': published_count}, status=200)

#     contract_type = request.data.get('contract_type')
#     if contract_type:
#         valid_types = [choice[0] for choice in profile._meta.get_field('contract_type').choices]
#         if contract_type not in valid_types:
#             return Response({'detail': 'Invalid contract type.'}, status=400)
#         profile.contract_type = contract_type

#     profile.has_contract = True
#     profile.contract_signed_at = timezone.now()
#     profile.save(update_fields=['has_contract', 'contract_signed_at', 'contract_type'])

#     # Mark all this author's stories in any pre-signed state → signed + ongoing
#     from apps.stories.models import Story
#     story_slug = request.data.get('slug', '').strip()
#     updated = Story.objects.filter(
#         author=user,
#         contract_status__in=['contract_sent', 'awaiting_signature', 'under_review'],
#     ).update(contract_status='signed', status='ongoing')
#     logger.info('accept_contract: updated %d stories for user %s', updated, user.username)

#     # If no stories matched above (edge case: status already moved), force the specific story
#     if updated == 0 and story_slug:
#         Story.objects.filter(author=user, slug=story_slug).update(
#             contract_status='signed', status='ongoing'
#         )
#         logger.info('accept_contract: force-updated story %s', story_slug)

#     # Mark ContractApplication as signed and save signature file
#     if story_slug:
#         try:
#             story = Story.objects.get(slug=story_slug, author=user)
#             app   = story.contract_application
#             app.status    = app.STATUS_SIGNED
#             app.signed_at = timezone.now()
#             app.save(update_fields=['status', 'signed_at'])

#             sig_file = request.FILES.get('signature')
#             if sig_file:
#                 from django.core.files.storage import default_storage
#                 from django.core.files.base import ContentFile
#                 default_storage.save(
#                     f'signatures/{user.id}_{story_slug}.png',
#                     ContentFile(sig_file.read()),
#                 )
#         except Exception as e:
#             logger.warning('accept_contract: ContractApplication update failed: %s', e)

#     published_count = Chapter.publish_held_chapters_for_author(user)
#     logger.info('accept_contract: published %d chapters for user %s', published_count, user.username)

#     # In-app notification
#     try:
#         from apps.notifications.services import on_contract_signed
#         from apps.stories.models import Story as _S
#         signed_story = _S.objects.filter(author=user, contract_status='signed').first()
#         if signed_story:
#             on_contract_signed(user, signed_story, published_count)
#     except Exception:
#         pass

#     return Response({
#         'status': 'contract_accepted',
#         'published_chapters': published_count,
#     })


# class EditorAssignmentListCreateView(generics.ListCreateAPIView):
#     """GET/POST /api/editorial/assignments/"""
#     serializer_class = EditorAssignmentSerializer
#     permission_classes = [IsCE]
#     queryset = EditorAssignment.objects.all().select_related('editor', 'supervisor')


# class AuthorEditorLinkListCreateView(generics.ListCreateAPIView):
#     """GET/POST /api/editorial/author-links/"""
#     serializer_class = AuthorEditorLinkSerializer
#     permission_classes = [IsCE]
#     queryset = AuthorEditorLink.objects.all().select_related('author', 'assigned_se')


# class EditorialTeamView(APIView):
#     """GET /api/editorial/team/ — editorial org overview."""
#     permission_classes = [IsCE]

#     def get(self, request):
#         data = {'ce': [], 'se': []}

#         for ce in User.objects.filter(role='ce'):
#             data['ce'].append({'id': ce.id, 'username': ce.username, 'email': ce.email})

#         for se in User.objects.filter(role='se'):
#             try:
#                 ce_sup = se.editorial_assignment.supervisor
#                 ce_name = ce_sup.username if ce_sup else None
#             except Exception:
#                 ce_name = None

#             pending_count = Chapter.objects.filter(
#                 story__author__editor_link__assigned_se=se,
#                 status=Chapter.STATUS_PENDING_REVIEW,
#             ).count()

#             data['se'].append({
#                 'id': se.id,
#                 'username': se.username,
#                 'email': se.email,
#                 'reports_to_ce': ce_name,
#                 'pending_count': pending_count,
#                 'author_count': se.sourced_authors.count(),
#                 'editor_code': se.editor_code or '',
#             })

#         return Response(data)


# class EditorialStatsView(APIView):
#     """GET /api/editorial/stats/ — role-aware editorial metrics."""
#     permission_classes = [IsSEOrAbove]

#     def get(self, request):
#         user = request.user

#         if user.role == 'se':
#             return Response({
#                 'pending_review_count': Chapter.objects.filter(
#                     story__author__editor_link__assigned_se=user,
#                     status=Chapter.STATUS_PENDING_REVIEW,
#                 ).count(),
#                 'approved_this_week': Chapter.objects.filter(
#                     reviewed_by_se=user,
#                     reviewed_at__gte=timezone.now() - timedelta(days=7),
#                     status=Chapter.STATUS_SE_APPROVED,
#                 ).count(),
#                 'author_count': user.sourced_authors.count(),
#             })

#         if user.role == 'ce':
#             return Response({
#                 'contract_ready_count': Chapter.objects.filter(status=Chapter.STATUS_SE_APPROVED).count(),
#                 'total_editors': User.objects.filter(role='se').count(),
#                 'se_count': User.objects.filter(role='se').count(),
#             })

#         return Response({})


# @api_view(['POST'])
# @permission_classes([permissions.AllowAny])
# def validate_editor_code(request):
#     logger = logging.getLogger(__name__)
#     logger.info(f'Validating editor code: {request.data}')
#     code = request.data.get('code', '').strip().upper()
#     if not code:
#         return Response({'valid': False, 'error': 'Code is required.'}, status=400)

#     try:
#         editor = User.objects.get(editor_code=code, role='se')
#         display = editor.get_full_name() or editor.username
#         author_count = editor.sourced_authors.count()
#         return Response({
#             'valid': True,
#             'editor_display_name': display,
#             'editor_role': editor.role,
#             'author_count': author_count,
#         })
#     except User.DoesNotExist:
#         return Response({'valid': False, 'error': 'Invalid editor code.'})


# @api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])
# def link_editor_by_code(request):
#     user = request.user
#     code = request.data.get('code', '').strip().upper()
#     link, error = AuthorEditorLink.link_by_code(user, code)
#     if error:
#         return Response({'error': error}, status=400)
#     from .serializers import AuthorEditorLinkSerializer
#     return Response({
#         'success': True,
#         'link': AuthorEditorLinkSerializer(link).data,
#     })


# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def my_editor_link(request):
#     user = request.user
#     try:
#         link = AuthorEditorLink.objects.select_related('assigned_se').get(author=user)
#         se = link.assigned_se
#         return Response({
#             'linked': True,
#             'link_method': link.link_method,
#             'assigned_at': link.assigned_at,
#             'se': {
#                 'display_name': se.get_full_name() or se.username if se else None,
#                 'author_count': se.sourced_authors.count() if se else 0,
#             } if se else None,
#         })
#     except AuthorEditorLink.DoesNotExist:
#         return Response({'linked': False, 'se': None})


# @api_view(['GET'])
# @permission_classes([IsSE])
# def my_editor_code(request):
#     user = request.user
#     code = user.editor_code or user.generate_editor_code()
#     return Response({
#         'editor_code': code,
#         'author_count': user.sourced_authors.count(),
#         'share_hint': f'Share this code with authors so they can link to you at signup: {code}',
#     })


"""
Editorial API Views
===================

Two-tier editorial hierarchy: SE (Senior Editor) and CE (Chief Editor).

SE flow:
  - Authors link to SE via invite code
  - SE reviews chapters submitted by their linked authors
  - SE can approve, request revision, remove, or escalate to CE

CE flow:
  - Reviews SE-approved chapters and sends contracts
  - Manages SE team via invites
"""

from datetime import timedelta
import logging

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chapters.models import Chapter
from apps.users.models import AuthorProfile
from .models import EditorAssignment, AuthorEditorLink
from .serializers import (
    EditorAssignmentSerializer,
    AuthorEditorLinkSerializer,
    ChapterReviewListSerializer,
    ChapterReviewDetailSerializer,
)
from .permissions import IsSEOrAbove, IsCE, IsSE

User = get_user_model()


# ─── Story-level SE review ────────────────────────────────────────────────────

class SEStoryQueueView(generics.ListAPIView):
    """GET /api/editorial/story-queue/?status=&search=
    Returns stories linked to this SE.
    status param: 'pending' (under_review), 'rejected', or empty/all (both sections).
    Each result includes a queue_section field: 'pending' | 'rejected'.
    """
    permission_classes = [IsSE]

    def get(self, request, *args, **kwargs):
        from apps.stories.models import Story
        from apps.editorial.models import ContractApplication
        from django.db.models import Q

        # Determine which contract statuses to fetch
        status_param = request.query_params.get('status', '').strip().lower()
        if status_param == 'pending':
            status_filter = ['under_review']
        elif status_param == 'rejected':
            status_filter = ['rejected']
        else:
            status_filter = ['under_review', 'rejected']

        qs = Story.objects.filter(
            contract_status__in=status_filter,
            author__editor_link__assigned_se=request.user,
        ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(book_code__iexact=search)
                | Q(title__icontains=search)
                | Q(author__username__icontains=search)
                | Q(author__author_code__iexact=search)
            )

        data = []
        for s in qs:
            chapters = list(
                s.chapters.order_by('chapter_number').values(
                    'id', 'chapter_number', 'title', 'status',
                    'word_count', 'created_at', 'se_note',
                )
            )
            try:
                app = s.contract_application
                app_status = app.status
                app_id = app.id
                se_note = app.se_note
                rejection_reason = app.rejection_reason if hasattr(app, 'rejection_reason') else app.se_note
            except ContractApplication.DoesNotExist:
                app_status = 'pending'
                app_id = None
                se_note = ''
                rejection_reason = ''

            data.append({
                'id':              s.id,
                'slug':            s.slug,
                'book_code':       s.book_code,
                'title':           s.title,
                'synopsis':        s.synopsis,
                'description':     s.description,
                'story_outline':   s.story_outline,
                'cover_image':     s.cover_image.url if s.cover_image else '',
                'status':          s.status,
                'contract_status': s.contract_status,
                # Tells the frontend which tab/section this story belongs to
                'queue_section':   'rejected' if s.contract_status == 'rejected' else 'pending',
                'word_count':      s.word_count,
                'total_chapters':  s.chapters.count(),
                'author': {
                    'id':           s.author.id,
                    'author_code':  s.author.author_code or '',
                    'username':     s.author.username,
                    'display_name': s.author.get_full_name() or s.author.username,
                    'email':        s.author.email,
                },
                'application': {
                    'id':              app_id,
                    'status':          app_status,
                    'note':            se_note,
                    'rejection_reason': rejection_reason,
                },
                'chapters': chapters,
                'submitted_at': s.updated_at,
            })

        pending_count  = sum(1 for d in data if d['queue_section'] == 'pending')
        rejected_count = sum(1 for d in data if d['queue_section'] == 'rejected')

        return Response({
            'count':          len(data),
            'pending_count':  pending_count,
            'rejected_count': rejected_count,
            'results':        data,
        })


class SEStoryDetailView(APIView):
    """GET /api/editorial/story-queue/<slug>/ — full story detail for SE review."""
    permission_classes = [IsSE]

    def get(self, request, slug):
        from apps.stories.models import Story
        from apps.editorial.models import ContractApplication

        story = get_object_or_404(
            Story,
            slug=slug,
            author__editor_link__assigned_se=request.user,
        )

        chapters = list(
            story.chapters.order_by('chapter_number').values(
                'id', 'chapter_number', 'title', 'status',
                'word_count', 'created_at', 'se_note', 'content',
            )
        )

        try:
            app = story.contract_application
            application = {
                'id': app.id, 'status': app.status,
                'note': app.se_note, 'applied_at': app.applied_at,
            }
        except ContractApplication.DoesNotExist:
            application = None

        try:
            app = story.contract_application
            rejection_reason = app.rejection_reason or app.se_note or ''
        except Exception:
            rejection_reason = ''

        return Response({
            'id':                  story.id,
            'slug':                story.slug,
            'book_code':           story.book_code,
            'queue_section':       'rejected' if story.contract_status == 'rejected' else 'pending',
            'title':               story.title,
            'synopsis':            story.synopsis,
            'story_outline':       story.story_outline,
            'description':         story.description,
            'cover_image':         story.cover_image.url if story.cover_image else '',
            'status':              story.status,
            'contract_status':     story.contract_status,
            'rejection_reason':    rejection_reason,
            'word_count':          story.word_count,
            'total_chapters':      story.chapters.count(),
            'tags':                list(story.tags.values('id', 'name')),
            'chapters_per_week':   story.chapters_per_week,
            'is_editors_pick':     story.is_editors_pick,
            'is_world_famous':     story.is_world_famous,
            'is_african_folktale': story.is_african_folktale,
            'is_featured':         story.is_featured,
            'is_free_download':    story.is_free_download,
            'author': {
                'id':           story.author.id,
                'author_code':  story.author.author_code or '',
                'username':     story.author.username,
                'display_name': story.author.get_full_name() or story.author.username,
                'email':        story.author.email,
            },
            'application': application,
            'chapters':    chapters,
        })


@api_view(['POST'])
@permission_classes([IsSE])
def se_approve_story(request, slug):
    """POST /api/editorial/story-queue/<slug>/approve/ — SE approves full story for CE."""
    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication

    story = get_object_or_404(
        Story, slug=slug,
        author__editor_link__assigned_se=request.user,
        contract_status__in=['under_review', 'rejected'],
    )
    note = request.data.get('note', '')

    # Approve all pending chapters on this story
    Chapter.objects.filter(
        story=story,
        status__in=[
            Chapter.STATUS_PENDING_REVIEW,
            Chapter.STATUS_SE_REVIEWING,
        ],
    ).update(
        status=Chapter.STATUS_SE_APPROVED,
        reviewed_by_se=request.user,
        reviewed_at=timezone.now(),
    )

    # Advance the contract application
    try:
        app = story.contract_application
        app.status = ContractApplication.STATUS_SE_APPROVED
        app.se_note = note
        app.se_reviewed_at = timezone.now()
        app.assigned_se = request.user
        app.save(update_fields=['status', 'se_note', 'se_reviewed_at', 'assigned_se'])
    except ContractApplication.DoesNotExist:
        ContractApplication.objects.create(
            story=story, author=story.author, assigned_se=request.user,
            status=ContractApplication.STATUS_SE_APPROVED,
            se_note=note, se_reviewed_at=timezone.now(),
        )

    # Move story to contract_sent stage (now visible to CE)
    story.contract_status = 'contract_sent'
    story.save(update_fields=['contract_status'])

    # Notify author
    try:
        from apps.notifications.services import on_se_approved
        on_se_approved(story.author, story)
    except Exception:
        pass

    return Response({'status': 'approved', 'story': story.slug})


@api_view(['POST'])
@permission_classes([IsSE])
def se_reject_story(request, slug):
    """POST /api/editorial/story-queue/<slug>/reject/ — SE rejects / requests revision."""
    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication

    story = get_object_or_404(
        Story, slug=slug,
        author__editor_link__assigned_se=request.user,
        contract_status__in=['under_review', 'rejected'],
    )
    reason = request.data.get('reason', '')
    action = request.data.get('action', 'revision')  # 'revision' or 'reject'

    if action == 'reject':
        new_contract = 'none'
        new_ch_status = Chapter.STATUS_REJECTED
        app_status = ContractApplication.STATUS_REJECTED
    else:
        new_contract = 'under_review'
        new_ch_status = Chapter.STATUS_SE_REVISION
        app_status = ContractApplication.STATUS_SE_REVIEW

    Chapter.objects.filter(
        story=story,
        status__in=[Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING],
    ).update(
        status=new_ch_status,
        se_note=reason,
        reviewed_by_se=request.user,
        reviewed_at=timezone.now(),
    )

    try:
        app = story.contract_application
        app.status = app_status
        app.se_note = reason
        app.se_reviewed_at = timezone.now()
        app.save(update_fields=['status', 'se_note', 'se_reviewed_at'])
    except ContractApplication.DoesNotExist:
        pass

    if action == 'reject':
        story.contract_status = 'rejected'
        story.status = 'draft'
        story.save(update_fields=['contract_status', 'status'])

    try:
        from apps.notifications.services import on_se_revision_requested, on_contract_rejected
        from apps.notifications.models import Notification
        from apps.notifications.services import create_notification
        if action == 'revision':
            on_se_revision_requested(story.author, story, reason)
        else:
            on_contract_rejected(story.author, story, reason=reason)
    except Exception:
        pass

    return Response({'status': action, 'story': story.slug})


@api_view(['POST'])
@permission_classes([IsSE])
def se_reopen_story(request, slug):
    """POST /api/editorial/story-queue/<slug>/reopen/
    SE moves a rejected story back to under_review so it re-enters the review pipeline.
    Optional body: { note: "reason for reopening" }
    """
    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication

    story = get_object_or_404(
        Story, slug=slug,
        author__editor_link__assigned_se=request.user,
        contract_status='rejected',
    )

    note = request.data.get('note', '').strip()

    story.contract_status = 'under_review'
    story.save(update_fields=['contract_status'])

    try:
        app = story.contract_application
        app.status = ContractApplication.STATUS_SE_REVIEW
        if note:
            app.se_note = note
        app.save(update_fields=['status', 'se_note'])
    except ContractApplication.DoesNotExist:
        ContractApplication.objects.create(
            story=story,
            author=story.author,
            assigned_se=request.user,
            status=ContractApplication.STATUS_SE_REVIEW,
            se_note=note,
        )

    try:
        from apps.notifications.services import create_notification
        from apps.notifications.models import Notification
        create_notification(
            user=story.author,
            notification_type=Notification.TYPE_SYSTEM,
            title='Your story is under review again',
            message=f'"{story.title}" has been reopened for review by your editor.',
            data={'screen': 'my_books', 'slug': story.slug},
        )
    except Exception:
        pass

    return Response({'status': 'reopened', 'story': story.slug})


@api_view(['POST'])
@permission_classes([IsSE])
def se_escalate_story_to_ce(request, slug):
    """POST /api/editorial/story-queue/<slug>/escalate/ — SE escalates story directly to CE."""
    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication

    story = get_object_or_404(
        Story, slug=slug,
        author__editor_link__assigned_se=request.user,
    )
    reasoning = request.data.get('reasoning', '')

    story.contract_status = 'contract_sent'
    story.save(update_fields=['contract_status'])

    try:
        app = story.contract_application
        app.status = ContractApplication.STATUS_SE_APPROVED
        app.se_note = f'CE Escalation: {reasoning}'
        app.se_reviewed_at = timezone.now()
        app.save(update_fields=['status', 'se_note', 'se_reviewed_at'])
    except ContractApplication.DoesNotExist:
        pass

    return Response({'status': 'escalated_to_ce', 'story': story.slug})



class EditorialQueueView(generics.ListAPIView):
    """GET /api/editorial/queue/ — list chapters awaiting editorial review."""
    serializer_class = ChapterReviewListSerializer
    permission_classes = [IsSEOrAbove]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ce':
            return Chapter.objects.filter(status=Chapter.STATUS_SE_APPROVED)

        if user.role == 'se':
            return Chapter.objects.filter(
                story__author__editor_link__assigned_se=user,
                status__in=[Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING],
            )

        return Chapter.objects.none()


class EditorialChapterDetailView(generics.RetrieveAPIView):
    """GET /api/editorial/reviews/<id>/"""
    serializer_class = ChapterReviewDetailSerializer
    permission_classes = [IsSEOrAbove]
    queryset = Chapter.objects.all()


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_approve(request, pk):
    """POST /api/editorial/reviews/<id>/approve/"""
    chapter = get_object_or_404(Chapter, pk=pk)
    if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING]:
        return Response(
            {'detail': 'Chapter is not eligible for SE approval.'},
            status=400,
        )
    chapter.status = Chapter.STATUS_SE_APPROVED
    chapter.reviewed_by_se = request.user
    chapter.reviewed_at = timezone.now()
    chapter.save(update_fields=['status', 'reviewed_by_se', 'reviewed_at'])
    return Response({'status': 'se_approved', 'chapter_id': chapter.id})


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_request_revision(request, pk):
    """POST /api/editorial/reviews/<id>/request-revision/"""
    chapter = get_object_or_404(Chapter, pk=pk)
    if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING]:
        return Response(
            {'detail': 'Chapter is not currently in SE review.'},
            status=400,
        )
    message = request.data.get('message', '')
    chapter.status = Chapter.STATUS_SE_REVISION
    chapter.se_note = message
    chapter.reviewed_by_se = request.user
    chapter.reviewed_at = timezone.now()
    chapter.save(update_fields=['status', 'se_note', 'reviewed_by_se', 'reviewed_at'])
    return Response({'status': 'se_revision_requested', 'chapter_id': chapter.id})


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_remove_content(request, pk):
    """POST /api/editorial/reviews/<id>/remove/ — SE removes content from platform."""
    chapter = get_object_or_404(Chapter, pk=pk)
    if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING, Chapter.STATUS_SE_REVISION]:
        return Response(
            {'detail': 'Chapter is not eligible for removal.'},
            status=400,
        )
    reason = request.data.get('reason', '')
    chapter.status = Chapter.STATUS_REJECTED
    chapter.se_note = f'Removed: {reason}' if reason else 'Removed by SE'
    chapter.reviewed_by_se = request.user
    chapter.reviewed_at = timezone.now()
    chapter.save(update_fields=['status', 'se_note', 'reviewed_by_se', 'reviewed_at'])
    return Response({'status': 'removed', 'chapter_id': chapter.id})


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_escalate_to_ce(request, pk):
    """POST /api/editorial/reviews/<id>/escalate-to-ce/ — SE escalates to Chief Editor."""
    chapter = get_object_or_404(Chapter, pk=pk)
    if chapter.status not in [Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING]:
        return Response(
            {'detail': 'Chapter is not eligible for CE escalation.'},
            status=400,
        )
    reasoning = request.data.get('reasoning', '')
    chapter.status = Chapter.STATUS_SE_APPROVED
    chapter.se_note = f'CE Escalation: {reasoning}' if reasoning else 'Escalated to CE by SE'
    chapter.reviewed_by_se = request.user
    chapter.reviewed_at = timezone.now()
    chapter.save(update_fields=['status', 'se_note', 'reviewed_by_se', 'reviewed_at'])
    return Response({'status': 'escalated_to_ce', 'chapter_id': chapter.id})


# ─── CE Story Review ──────────────────────────────────────────────────────────

class CEStoryQueueView(APIView):
    """GET /api/editorial/ce-story-queue/ — SE-approved stories awaiting CE action."""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.stories.models import Story
        from apps.editorial.models import ContractApplication
        from django.db.models import Q

        qs = Story.objects.filter(
            contract_status='contract_sent',
        ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(book_code__iexact=search)
                | Q(title__icontains=search)
                | Q(author__username__icontains=search)
                | Q(author__author_code__iexact=search)
            )

        data = []
        for s in qs:
            chapters = list(
                s.chapters.order_by('chapter_number').values(
                    'id', 'chapter_number', 'title', 'status', 'word_count', 'created_at',
                )
            )
            try:
                app = s.contract_application
                app_data = {
                    'id': app.id, 'status': app.status,
                    'se_note': app.se_note,
                    'applied_at': app.applied_at,
                    'assigned_se': app.assigned_se.username if app.assigned_se else None,
                }
            except ContractApplication.DoesNotExist:
                app_data = None

            # Resolve which SE approved this story
            try:
                se = s.author.editor_link.assigned_se
                se_info = {'username': se.username, 'display_name': se.get_full_name() or se.username} if se else None
            except Exception:
                se_info = None

            data.append({
                'id':              s.id,
                'slug':            s.slug,
                'book_code':       s.book_code,
                'title':           s.title,
                'synopsis':        s.synopsis,
                'description':     s.description,
                'story_outline':   s.story_outline,
                'cover_image':     s.cover_image.url if s.cover_image else '',
                'status':          s.status,
                'contract_status': s.contract_status,
                'word_count':      s.word_count,
                'total_chapters':  s.chapters.count(),
                'author': {
                    'id':           s.author.id,
                    'author_code':  s.author.author_code or '',
                    'username':     s.author.username,
                    'display_name': s.author.get_full_name() or s.author.username,
                    'email':        s.author.email,
                },
                'approved_by_se': se_info,
                'application':    app_data,
                'chapters':       chapters,
            })

        return Response({'count': len(data), 'results': data})


class CEStoryDetailView(APIView):
    """GET /api/editorial/ce-story-queue/<slug>/ — full story detail for CE."""
    permission_classes = [IsCE]

    def get(self, request, slug):
        from apps.stories.models import Story
        from apps.editorial.models import ContractApplication

        story = get_object_or_404(Story, slug=slug)

        chapters = list(
            story.chapters.order_by('chapter_number').values(
                'id', 'chapter_number', 'title', 'status',
                'word_count', 'created_at', 'se_note', 'content',
            )
        )

        try:
            app = story.contract_application
            application = {
                'id': app.id, 'status': app.status, 'se_note': app.se_note,
                'applied_at': app.applied_at, 'se_reviewed_at': app.se_reviewed_at,
                'assigned_se': app.assigned_se.username if app.assigned_se else None,
            }
        except ContractApplication.DoesNotExist:
            application = None

        try:
            se = story.author.editor_link.assigned_se
            se_info = {'username': se.username, 'display_name': se.get_full_name() or se.username} if se else None
        except Exception:
            se_info = None

        return Response({
            'id':                  story.id,
            'slug':                story.slug,
            'title':               story.title,
            'synopsis':            story.synopsis,
            'description':         story.description,
            'story_outline':       story.story_outline,
            'cover_image':         story.cover_image.url if story.cover_image else '',
            'status':              story.status,
            'contract_status':     story.contract_status,
            'word_count':          story.word_count,
            'total_chapters':      story.chapters.count(),
            'tags':                list(story.tags.values('id', 'name')),
            'chapters_per_week':   story.chapters_per_week,
            'is_editors_pick':     story.is_editors_pick,
            'is_world_famous':     story.is_world_famous,
            'is_african_folktale': story.is_african_folktale,
            'is_featured':         story.is_featured,
            'is_free_download':    story.is_free_download,
            'editors_pick_expires_at':     story.editors_pick_expires_at.isoformat() if story.editors_pick_expires_at else None,
            'world_famous_expires_at':     story.world_famous_expires_at.isoformat() if story.world_famous_expires_at else None,
            'african_folktale_expires_at': story.african_folktale_expires_at.isoformat() if story.african_folktale_expires_at else None,
            'featured_expires_at':         story.featured_expires_at.isoformat() if story.featured_expires_at else None,
            'free_download_expires_at':    story.free_download_expires_at.isoformat() if story.free_download_expires_at else None,
            'author': {
                'id':           story.author.id,
                'username':     story.author.username,
                'display_name': story.author.get_full_name() or story.author.username,
                'email':        story.author.email,
            },
            'approved_by_se': se_info,
            'application':    application,
            'chapters':       chapters,
        })


@api_view(['POST'])
@permission_classes([IsCE])
def ce_send_contract_story(request, slug):
    """POST /api/editorial/ce-story-queue/<slug>/send-contract/ — CE sends contract to author."""
    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication

    story = get_object_or_404(Story, slug=slug, contract_status='contract_sent')

    contract_type = request.data.get('contract_type', 'non_exclusive')
    ce_note = request.data.get('note', '')

    now = timezone.now()
    try:
        app = story.contract_application
        app.status = ContractApplication.STATUS_CONTRACT_SENT
        app.contract_sent_at = now
        app.ce_signed_by = request.user
        app.ce_signed_at = now
        app.se_note = (app.se_note + '\nCE note: ' + ce_note).strip() if ce_note else app.se_note
        app.contract_type = contract_type
        app.save(update_fields=['status', 'contract_sent_at', 'ce_signed_by', 'ce_signed_at', 'se_note', 'contract_type'])
    except ContractApplication.DoesNotExist:
        ContractApplication.objects.create(
            story=story, author=story.author,
            status=ContractApplication.STATUS_CONTRACT_SENT,
            contract_sent_at=now,
            ce_signed_by=request.user,
            ce_signed_at=now,
            contract_type=contract_type,
        )

    # ── Send contract email in background thread (avoids 502 on Render) ──
    import threading as _threading
    _slug_cap         = story.slug
    _author_email     = story.author.email
    _author_name      = story.author.first_name or story.author.username
    _story_title      = story.title
    _contract_type_cap = contract_type
    _ce_note_cap      = ce_note

    def _send_contract_email_async():
        import logging
        _log = logging.getLogger(__name__)
        try:
            from django.core.mail import send_mail
            from django.conf import settings as _settings
            platform       = 'Novelux'
            contract_label = 'Exclusive' if _contract_type_cap == 'exclusive' else 'Non-Exclusive'
            sign_url       = f'https://www.novelux.app/my-books/{_slug_cap}/contract/'
            subject        = f'Your {platform} contract offer — "{_story_title}"'
            text_body      = (
                f'Hello {_author_name},\n\n'
                f'congratulations!\n\n'
                f'Your book "{_story_title}" has been reviewed, and we are offering you a {contract_label} contract.\n\n'
                f'You can review carefully and sign your contract successfully using the attached link below:\n{sign_url}\n\n'
                f'We\'re excited to have you as part of NoveluX and looking forward to supporting your journey as an author!\n\n'
                'Warm regards,\n'
                + (f'CE note: {_ce_note_cap}\n\n' if _ce_note_cap else '')
                + f'– The {platform} Editorial Team'
            )
            send_mail(
                subject=subject, message=text_body,
                from_email=_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[_author_email],
                fail_silently=False,
            )
            _log.info('Contract email sent to %s for story %s', _author_email, _slug_cap)
        except Exception as _e:
            _log.error('Contract email failed for %s: %s', _slug_cap, _e)

    _threading.Thread(target=_send_contract_email_async, daemon=True).start()

    # ── In-app notification + push ──────────────────────────────────────
    try:
        from apps.notifications.services import on_contract_sent
        on_contract_sent(story.author, story, contract_type)
    except Exception:
        pass

    # Advance story status so it no longer appears in the CE pending queue on reload
    story.contract_status = 'awaiting_signature'
    story.save(update_fields=['contract_status'])

    return Response({'status': 'contract_sent', 'story': story.slug})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_reject_story(request, slug):
    """POST /api/editorial/ce-story-queue/<slug>/reject/ — CE rejects or sends back to SE."""
    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication

    story = get_object_or_404(Story, slug=slug)
    reason = request.data.get('reason', '')
    action = request.data.get('action', 'send_back')  # 'send_back' | 'reject'

    if action == 'reject':
        story.contract_status = 'rejected'
        story.status = 'draft'
        story.save(update_fields=['contract_status', 'status'])
        try:
            app = story.contract_application
            app.status = ContractApplication.STATUS_REJECTED
            app.rejection_reason = reason
            app.rejected_at = timezone.now()
            app.save(update_fields=['status', 'rejection_reason', 'rejected_at'])
        except ContractApplication.DoesNotExist:
            pass
        notify_title = 'Contract not approved'
        notify_body  = f'"{story.title}" was not approved for a contract at this time.'
    else:
        # Send back to SE for re-review
        story.contract_status = 'under_review'
        story.save(update_fields=['contract_status'])
        try:
            app = story.contract_application
            app.status = ContractApplication.STATUS_SE_REVIEW
            app.se_note = f'CE returned for revision: {reason}'
            app.save(update_fields=['status', 'se_note'])
        except ContractApplication.DoesNotExist:
            pass
        notify_title = 'Story returned for revision'
        notify_body  = f'"{story.title}" has been returned by the Chief Editor for further revision.'

    try:
        from apps.notifications.services import create_notification
        from apps.notifications.models import Notification
        create_notification(
            user=story.author,
            notification_type=Notification.TYPE_SYSTEM,
            title=notify_title,
            message=notify_body,
            data={'screen': 'my_books', 'slug': story.slug},
        )
    except Exception:
        pass

    return Response({'status': action, 'story': story.slug})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_edit_story_note(request, slug):
    """POST /api/editorial/ce-story-queue/<slug>/note/ — CE adds a note to a story application."""
    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication

    story = get_object_or_404(Story, slug=slug)
    note = request.data.get('note', '').strip()

    try:
        app = story.contract_application
        app.se_note = note
        app.save(update_fields=['se_note'])
        return Response({'status': 'note_saved'})
    except ContractApplication.DoesNotExist:
        return Response({'detail': 'No contract application for this story.'}, status=404)


@api_view(['POST'])
@permission_classes([IsCE])
def toggle_library_banner(request, slug):
    """POST /api/editorial/stories/<slug>/library-banner/
    CE pins or unpins a story from the library screen banner carousel.
    Body: { "enabled": true } or { "enabled": false }
    """
    from apps.stories.models import Story
    story = get_object_or_404(Story, slug=slug)
    enabled = str(request.data.get('enabled', 'true')).lower() in ('true', '1', 'yes')
    story.is_library_banner = enabled
    story.save(update_fields=['is_library_banner'])
    return Response({
        'slug': story.slug,
        'is_library_banner': story.is_library_banner,
        'status': 'pinned' if enabled else 'unpinned',
    })


@api_view(['POST'])
@permission_classes([IsCE])
def ce_editorial_sign(request, slug):
    """POST /api/editorial/ce-story-queue/<slug>/ce-sign/
    CE performs editorial signing (platform-side signature) on a story.
    Works on stories in 'contract_sent' or 'awaiting_signature' state.
    """
    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication

    story = get_object_or_404(Story, slug=slug)

    if story.contract_status not in ('contract_sent', 'awaiting_signature'):
        return Response(
            {'detail': 'Story must be in contract_sent or awaiting_signature state for CE signing.'},
            status=400,
        )

    try:
        app = story.contract_application
        app.ce_signed_by = request.user
        app.ce_signed_at = timezone.now()
        app.save(update_fields=['ce_signed_by', 'ce_signed_at'])
    except ContractApplication.DoesNotExist:
        ContractApplication.objects.create(
            story=story,
            author=story.author,
            ce_signed_by=request.user,
            ce_signed_at=timezone.now(),
            status=ContractApplication.STATUS_CONTRACT_SENT,
        )

    return Response({'status': 'ce_signed', 'story': story.slug})


@api_view(['POST'])
@permission_classes([IsCE])
def assign_author_to_se(request):
    """POST /api/editorial/assign-author/
    CE assigns an unlinked author to one of their SEs.
    Body: { author_id: int, se_id: int }
    """
    from apps.editorial.models import AuthorEditorLink

    author_id = request.data.get('author_id')
    se_id = request.data.get('se_id')

    if not author_id or not se_id:
        return Response({'detail': 'author_id and se_id are required.'}, status=400)

    author = get_object_or_404(User, pk=author_id, role='author')
    se = get_object_or_404(User, pk=se_id, role='se')

    # Verify the SE is under this CE
    try:
        assignment = se.editorial_assignment
        if assignment.supervisor != request.user:
            return Response({'detail': 'That SE does not report to you.'}, status=403)
    except Exception:
        # If no EditorAssignment, allow CEs to assign any SE (fallback)
        pass

    link, created = AuthorEditorLink.objects.update_or_create(
        author=author,
        defaults={
            'assigned_se': se,
            'link_method': AuthorEditorLink.LINK_MANUAL,
            'notes': f'Manually assigned by CE {request.user.username}',
        },
    )

    return Response({
        'status': 'assigned',
        'author': author.username,
        'se': se.username,
        'created': created,
    })



class CEEscalationsView(generics.ListAPIView):
    """GET /api/editorial/ce-escalations/ — chapters approved by SE and awaiting CE contract."""
    serializer_class = ChapterReviewListSerializer
    permission_classes = [IsCE]

    def get_queryset(self):
        return Chapter.objects.filter(status=Chapter.STATUS_SE_APPROVED)


@api_view(['POST'])
@permission_classes([IsCE])
def ce_send_contract(request, pk):
    """POST /api/editorial/reviews/<id>/ce-approve/ — send contract to author."""
    chapter = get_object_or_404(Chapter, pk=pk)
    if chapter.status != Chapter.STATUS_SE_APPROVED:
        return Response(
            {'detail': 'Only SE-approved chapters may be moved to contract stage.'},
            status=400,
        )
    chapter.status = Chapter.STATUS_CONTRACT_SENT
    chapter.save(update_fields=['status'])
    return Response({'status': 'contract_sent', 'chapter_id': chapter.id})


def _sync_exclusive_flag(user, profile):
    """Story.is_exclusive is derived from the signed contract's type —
    authors cannot set it themselves. Called after a contract is signed."""
    from apps.stories.models import Story
    for s in Story.objects.filter(
            author=user, contract_status='signed', is_exclusive=False):
        try:
            ctype = s.contract_application.contract_type
        except Exception:
            ctype = getattr(profile, 'contract_type', '')
        if ctype == 'exclusive':
            Story.objects.filter(pk=s.pk).update(is_exclusive=True)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def accept_contract(request):
    """POST /api/editorial/contracts/accept/ — author accepts a contract and publishes held chapters."""
    import logging
    logger = logging.getLogger(__name__)

    user = request.user
    if user.role != 'author':
        return Response({'detail': 'Only authors may accept contracts.'}, status=403)

    profile, _ = AuthorProfile.objects.get_or_create(user=user)
    if profile.has_contract:
        # Already signed — still ensure story/chapter statuses are correct
        from apps.stories.models import Story
        Story.objects.filter(author=user).filter(
            contract_status__in=['contract_sent', 'awaiting_signature', 'under_review']
        ).update(contract_status='signed', contract_eligible=False, status='ongoing')
        _sync_exclusive_flag(user, profile)
        published_count = Chapter.publish_held_chapters_for_author(user)
        return Response({'detail': 'Contract already accepted.', 'published_chapters': published_count}, status=200)

    contract_type = request.data.get('contract_type')
    if contract_type:
        valid_types = [choice[0] for choice in profile._meta.get_field('contract_type').choices]
        if contract_type not in valid_types:
            return Response({'detail': 'Invalid contract type.'}, status=400)
        profile.contract_type = contract_type

    profile.has_contract = True
    profile.contract_signed_at = timezone.now()
    profile.save(update_fields=['has_contract', 'contract_signed_at', 'contract_type'])

    from apps.stories.models import Story
    story_slug = request.data.get('slug', '').strip()
    from django.db.models import F
    updated = Story.objects.filter(
        author=user,
        contract_status='awaiting_signature',
    ).update(contract_status='signed', contract_eligible=False, status='ongoing', words_at_signing=F('word_count'))
    logger.info('accept_contract: signed %d stories for user %s', updated, user.username)

    # If the specific story wasn't matched, verify it is in awaiting_signature before force-updating
    if updated == 0 and story_slug:
        force_qs = Story.objects.filter(author=user, slug=story_slug, contract_status='awaiting_signature')
        if force_qs.exists():
            force_qs.update(contract_status='signed', contract_eligible=False, status='ongoing', words_at_signing=F('word_count'))
            logger.info('accept_contract: force-signed story %s', story_slug)
        else:
            logger.warning('accept_contract: story %s not in awaiting_signature, refusing sign', story_slug)
            return Response({'detail': 'Contract has not been sent yet. Please wait for the editorial team.'}, status=400)

    # Mark ContractApplication as signed and save signature file
    if story_slug:
        try:
            story = Story.objects.get(slug=story_slug, author=user)
            app   = story.contract_application
            app.status    = app.STATUS_SIGNED
            app.signed_at = timezone.now()
            app.save(update_fields=['status', 'signed_at'])

            sig_file = request.FILES.get('signature')
            if sig_file:
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                default_storage.save(
                    f'signatures/{user.id}_{story_slug}.png',
                    ContentFile(sig_file.read()),
                )
        except Exception as e:
            logger.warning('accept_contract: ContractApplication update failed: %s', e)

    # Exclusive contracts mark the story platform-exclusive
    _sync_exclusive_flag(user, profile)

    # Chapters stay held — they publish automatically once the post-contract
    # word count threshold is hit (see Chapter._check_editorial_trigger Case A).
    published_count = 0
    logger.info('accept_contract: contract signed for user %s — story will go live after word threshold', user.username)

    # Notifications: author gets "contract signed" alert; bookmarkers get "book is live" push
    try:
        from apps.notifications.services import on_contract_signed, on_book_signed_live
        from apps.stories.models import Story as _S
        signed_story = _S.objects.filter(author=user, contract_status='signed').first()
        if signed_story:
            on_contract_signed(user, signed_story, published_count)
            on_book_signed_live(signed_story)
    except Exception:
        pass

    return Response({
        'status': 'contract_accepted',
        'published_chapters': published_count,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def decline_contract(request):
    """POST /api/editorial/contracts/decline/ — author declines a contract sent to them.
    Requires a reason so the editorial team knows why the author backed out.
    """
    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication

    user = request.user
    if user.role != 'author':
        return Response({'detail': 'Only authors may decline contracts.'}, status=403)

    reason = request.data.get('reason', '').strip()
    if not reason:
        return Response({'detail': 'Please tell us why you are declining this contract.'}, status=400)

    story_slug = request.data.get('slug', '').strip()
    qs = Story.objects.filter(author=user, contract_status='awaiting_signature')
    if story_slug:
        qs = qs.filter(slug=story_slug)
    story = qs.first()
    if not story:
        return Response({'detail': 'No contract awaiting your signature was found.'}, status=400)

    story.contract_status = 'rejected'
    story.status = 'draft'
    story.save(update_fields=['contract_status', 'status'])

    try:
        app = story.contract_application
        app.status = ContractApplication.STATUS_REJECTED
        app.rejection_reason = reason
        app.rejected_at = timezone.now()
        app.save(update_fields=['status', 'rejection_reason', 'rejected_at'])
    except ContractApplication.DoesNotExist:
        pass

    try:
        from apps.notifications.services import on_contract_declined_by_author
        on_contract_declined_by_author(story, reason)
    except Exception:
        pass

    return Response({'status': 'contract_declined', 'story': story.slug})


class EditorAssignmentListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/editorial/assignments/"""
    serializer_class = EditorAssignmentSerializer
    permission_classes = [IsCE]
    queryset = EditorAssignment.objects.all().select_related('editor', 'supervisor')


class AuthorEditorLinkListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/editorial/author-links/"""
    serializer_class = AuthorEditorLinkSerializer
    permission_classes = [IsCE]
    queryset = AuthorEditorLink.objects.all().select_related('author', 'assigned_se')


class EditorialTeamView(APIView):
    """GET /api/editorial/team/ — editorial org overview."""
    permission_classes = [IsCE]

    def get(self, request):
        data = {'ce': [], 'se': []}

        for ce in User.objects.filter(role='ce'):
            data['ce'].append({'id': ce.id, 'username': ce.username, 'email': ce.email})

        for se in User.objects.filter(role='se'):
            try:
                ce_sup = se.editorial_assignment.supervisor
                ce_name = ce_sup.username if ce_sup else None
            except Exception:
                ce_name = None

            pending_count = Chapter.objects.filter(
                story__author__editor_link__assigned_se=se,
                status=Chapter.STATUS_PENDING_REVIEW,
            ).count()

            data['se'].append({
                'id': se.id,
                'username': se.username,
                'email': se.email,
                'reports_to_ce': ce_name,
                'pending_count': pending_count,
                'author_count': se.sourced_authors.count(),
                'editor_code': se.editor_code or '',
            })

        return Response(data)


class EditorialStatsView(APIView):
    """GET /api/editorial/stats/ — role-aware editorial metrics."""
    permission_classes = [IsSEOrAbove]

    def get(self, request):
        user = request.user

        if user.role == 'se':
            return Response({
                'pending_review_count': Chapter.objects.filter(
                    story__author__editor_link__assigned_se=user,
                    status=Chapter.STATUS_PENDING_REVIEW,
                ).count(),
                'approved_this_week': Chapter.objects.filter(
                    reviewed_by_se=user,
                    reviewed_at__gte=timezone.now() - timedelta(days=7),
                    status=Chapter.STATUS_SE_APPROVED,
                ).count(),
                'author_count': user.sourced_authors.count(),
            })

        if user.role == 'ce':
            return Response({
                'contract_ready_count': Chapter.objects.filter(status=Chapter.STATUS_SE_APPROVED).count(),
                'total_editors': User.objects.filter(role='se').count(),
                'se_count': User.objects.filter(role='se').count(),
            })

        return Response({})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_editor_code(request):
    logger = logging.getLogger(__name__)
    logger.info(f'Validating editor code: {request.data}')
    code = request.data.get('code', '').strip().upper()
    if not code:
        return Response({'valid': False, 'error': 'Code is required.'}, status=400)

    try:
        editor = User.objects.get(editor_code=code, role='se')
        display = editor.get_full_name() or editor.username
        author_count = editor.sourced_authors.count()
        return Response({
            'valid': True,
            'editor_display_name': display,
            'editor_role': editor.role,
            'author_count': author_count,
        })
    except User.DoesNotExist:
        return Response({'valid': False, 'error': 'Invalid editor code.'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def link_editor_by_code(request):
    user = request.user
    code = request.data.get('code', '').strip().upper()
    link, error = AuthorEditorLink.link_by_code(user, code)
    if error:
        return Response({'error': error}, status=400)
    from .serializers import AuthorEditorLinkSerializer
    return Response({
        'success': True,
        'link': AuthorEditorLinkSerializer(link).data,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_editor_link(request):
    user = request.user
    try:
        link = AuthorEditorLink.objects.select_related('assigned_se').get(author=user)
        se = link.assigned_se
        return Response({
            'linked': True,
            'link_method': link.link_method,
            'assigned_at': link.assigned_at,
            'se': {
                'display_name': se.get_full_name() or se.username if se else None,
                'email': se.email if se else None,
                'author_count': se.sourced_authors.count() if se else 0,
            } if se else None,
        })
    except AuthorEditorLink.DoesNotExist:
        return Response({'linked': False, 'se': None})


@api_view(['GET'])
@permission_classes([IsSE])
def my_editor_code(request):
    user = request.user
    code = user.editor_code or user.generate_editor_code()
    return Response({
        'editor_code': code,
        'author_count': user.sourced_authors.count(),
        'share_hint': f'Share this code with authors so they can link to you at signup: {code}',
    })


# ── Editor Invite API endpoints ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsCE])
def invite_list(request):
    """GET /api/editorial/invites/ — list all invites created by this CE."""
    from apps.editorial.models import EditorInvite
    from django.utils import timezone

    # Auto-expire any past-due pending invites
    EditorInvite.objects.filter(
        status=EditorInvite.STATUS_PENDING,
        expires_at__lt=timezone.now(),
    ).update(status=EditorInvite.STATUS_EXPIRED)

    invites = EditorInvite.objects.filter(
        invited_by=request.user,
    ).select_related('supervisor', 'accepted_by').order_by('-created_at')[:100]

    data = [
        {
            'id':          inv.id,
            'email':       inv.email,
            'role':        inv.role,
            'status':      inv.status,
            'created_at':  inv.created_at.isoformat(),
            'expires_at':  inv.expires_at.isoformat(),
            'accepted_at': inv.accepted_at.isoformat() if inv.accepted_at else None,
            'supervisor':  inv.supervisor.get_full_name() or inv.supervisor.username if inv.supervisor else None,
            'notes':       inv.notes,
        }
        for inv in invites
    ]
    return Response(data)


@api_view(['POST'])
@permission_classes([IsCE])
def invite_revoke(request, pk):
    """POST /api/editorial/invites/<id>/revoke/ — revoke a pending invite."""
    from apps.editorial.models import EditorInvite

    invite = get_object_or_404(EditorInvite, pk=pk, invited_by=request.user)
    if invite.status != EditorInvite.STATUS_PENDING:
        return Response({'detail': f'Cannot revoke an invite with status "{invite.status}".'}, status=400)
    invite.status = EditorInvite.STATUS_REVOKED
    invite.save(update_fields=['status'])
    return Response({'ok': True, 'status': 'revoked'})


@api_view(['POST'])
@permission_classes([IsCE])
def invite_resend(request, pk):
    """POST /api/editorial/invites/<id>/resend/ — resend the invite email."""
    from apps.editorial.models import EditorInvite
    from apps.editorial.tasks import send_editor_invite_email

    invite = get_object_or_404(EditorInvite, pk=pk, invited_by=request.user)
    if invite.status not in (EditorInvite.STATUS_PENDING, EditorInvite.STATUS_EXPIRED):
        return Response({'detail': 'Only pending or expired invites can be resent.'}, status=400)

    # Re-activate expired invites with a fresh expiry
    if invite.status == EditorInvite.STATUS_EXPIRED:
        from django.utils import timezone
        import datetime
        invite.status     = EditorInvite.STATUS_PENDING
        invite.expires_at = timezone.now() + datetime.timedelta(days=7)
        invite.save(update_fields=['status', 'expires_at'])

    try:
        send_editor_invite_email(invite, request)
        email_sent = True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error('Resend invite email failed: %s', e)
        email_sent = False

    return Response({'ok': True, 'email_sent': email_sent})    

def _kyc_detail(kyc, request):
    """Serialise an AuthorKYC for SE / CE review dashboards."""
    def _url(field):
        return request.build_absolute_uri(field.url) if field else None

    return {
        'id':                   kyc.pk,
        'author_id':            kyc.user_id,
        'author_username':      kyc.user.username,
        'status':               kyc.status,
        'id_type':              kyc.id_type,
        'full_name':            kyc.full_name,
        'date_of_birth':        str(kyc.date_of_birth) if kyc.date_of_birth else None,
        'id_number':            kyc.id_number,
        'country':              kyc.country,
        'id_front':             _url(kyc.id_front),
        'id_back':              _url(kyc.id_back),
        # OCR
        'ocr_name':             kyc.ocr_name,
        'ocr_dob':              str(kyc.ocr_dob) if kyc.ocr_dob else None,
        'ocr_id_number':        kyc.ocr_id_number,
        # Match indicators
        'name_match_score':     kyc.name_match_score,   # 0-100
        'dob_match':            kyc.dob_match,
        'overall_match_score':  kyc.overall_match_score,
        'age_valid':            kyc.age_valid,
        # Review
        'rejection_reason':     kyc.rejection_reason,
        'admin_notes':          kyc.admin_notes,
        'submitted_at':         kyc.submitted_at,
        'reviewed_at':          kyc.reviewed_at,
    }


# ── SE directory (public — for contract application SE picker) ─────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def se_list(request):
    """
    GET /api/editorial/se-list/
    Returns all active SEs that authors can choose from when applying for a contract.
    Includes each SE's current author load so the app can optionally display it.
    Also includes a 'random' option representing platform auto-assignment.
    """
    _User = get_user_model()

    ses = _User.objects.filter(role='se').annotate(
        author_count=models.Count('sourced_authors')
    ).order_by('author_count', 'username')

    data = []
    for se in ses:
        pen = ''
        try:
            pen = se.author_profile.pen_name or ''
        except AttributeError:
            pass
        data.append({
            'id':           se.pk,
            'username':     se.username,
            'display_name': pen.strip() if pen.strip() else se.username,
            'avatar':       request.build_absolute_uri(se.avatar.url) if se.avatar else None,
            'bio':          se.bio,
            'author_count': se.author_count,
        })

    # Append the 'let platform decide' sentinel option
    data.append({
        'id':           'random',
        'username':     'random',
        'display_name': 'Let the platform assign an editor for me',
        'avatar':       None,
        'bio':          'The platform will automatically assign the best available Senior Editor for your work.',
        'author_count': None,
    })

    return Response(data)


def _link_author_to_se(author, se, method, notes=''):
    """
    Create or update an AuthorEditorLink.
    Returns (link, se) — se may be None if random assignment has no SEs available.
    """
    _User = get_user_model()

    if se is None and method in (AuthorEditorLink.LINK_AUTO, AuthorEditorLink.LINK_CHOSEN):
        # Pick the SE with the fewest active authors
        se = (
            _User.objects
            .filter(role='se')
            .annotate(author_count=models.Count('sourced_authors'))
            .order_by('author_count', '?')
            .first()
        )

    link, created = AuthorEditorLink.objects.update_or_create(
        author=author,
        defaults={
            'assigned_se': se,
            'link_method': method,
            'notes': notes,
        },
    )
    return link, se


class SEKYCListView(generics.ListAPIView):
    """GET /api/editorial/kyc/  — SE lists KYC submissions for their assigned authors."""
    permission_classes = [IsSEOrAbove]

    def list(self, request, *args, **kwargs):
        from apps.users.models import AuthorKYC
        from apps.editorial.models import AuthorEditorLink

        author_ids = AuthorEditorLink.objects.filter(
            assigned_se=request.user
        ).values_list('author_id', flat=True)

        status_filter = request.query_params.get('status')
        qs = AuthorKYC.objects.filter(user_id__in=author_ids).select_related('user')
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.order_by('-submitted_at')

        return Response([_kyc_detail(k, request) for k in qs])


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_review_kyc(request, pk):
    """
    POST /api/editorial/kyc/<id>/se-review/
    SE approves or rejects a KYC from one of their assigned authors.
    Body: { "action": "approve"|"reject", "note": "...", "rejection_reason": "..." }
    """
    from apps.users.models import AuthorKYC
    from apps.editorial.models import AuthorEditorLink

    kyc = get_object_or_404(AuthorKYC, pk=pk)

    # SE can only review their own authors — same freedom as CE otherwise
    # (any status can be acted on, not just 'under_review').
    if not AuthorEditorLink.objects.filter(assigned_se=request.user, author=kyc.user).exists():
        return Response({'detail': 'This author is not assigned to you.'}, status=403)

    action = request.data.get('action', '').strip()
    if action not in ('approve', 'reject'):
        return Response({'detail': "action must be 'approve' or 'reject'"}, status=400)

    kyc.status           = AuthorKYC.STATUS_APPROVED if action == 'approve' else AuthorKYC.STATUS_REJECTED
    kyc.rejection_reason = request.data.get('rejection_reason', '').strip()
    kyc.admin_notes      = request.data.get('note', '').strip()
    kyc.reviewed_by      = request.user
    kyc.reviewed_at      = timezone.now()
    kyc.save(update_fields=[
        'status', 'rejection_reason', 'admin_notes', 'reviewed_by', 'reviewed_at'
    ])

    try:
        from apps.notifications.services import create_notification
        if action == 'approve':
            msg = 'Your identity verification has been approved.'
        else:
            msg = f'Your identity verification was not approved. {kyc.rejection_reason}'
        create_notification(kyc.user, 'kyc_update', msg)
    except Exception:
        pass

    return Response({'ok': True, 'status': kyc.status})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_review_kyc(request, pk):
    """POST /api/editorial/kyc/<id>/review/  — CE approves or rejects an author KYC."""
    from apps.users.models import AuthorKYC

    kyc    = get_object_or_404(AuthorKYC, pk=pk)
    action = request.data.get('action', '').strip()   # 'approve' | 'reject'
    note   = request.data.get('note', '').strip()

    if action not in ('approve', 'reject'):
        return Response({'detail': "action must be 'approve' or 'reject'"}, status=400)

    kyc.status           = AuthorKYC.STATUS_APPROVED if action == 'approve' else AuthorKYC.STATUS_REJECTED
    kyc.rejection_reason = request.data.get('rejection_reason', '').strip()
    kyc.admin_notes      = note
    kyc.reviewed_by      = request.user
    kyc.reviewed_at      = timezone.now()
    kyc.save(update_fields=[
        'status', 'rejection_reason', 'admin_notes', 'reviewed_by', 'reviewed_at'
    ])

    try:
        from apps.notifications.services import create_notification
        msg = (
            'Your identity verification has been approved.'
            if action == 'approve'
            else f'Your identity verification was not approved. {kyc.rejection_reason}'
        )
        create_notification(kyc.user, 'kyc_update', msg)
    except Exception:
        pass

    return Response({'ok': True, 'status': kyc.status})


@api_view(['GET'])
@permission_classes([IsSEOrAbove])
def se_story_panel(request, slug):
    """GET /api/editorial/story-queue/<slug>/panel/
    Full story + author detail for the SE Contract Pipeline panel.
    """
    from apps.stories.models import Story, Bookmark, ReadingProgress
    from apps.chapters.models import Chapter
    from apps.users.models import AuthorKYC, AuthorProfile
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    import datetime

    story = get_object_or_404(
        Story,
        slug=slug,
        author__editor_link__assigned_se=request.user,
    )
    author = story.author

    # Author profile + KYC
    try:
        profile = author.author_profile
    except AuthorProfile.DoesNotExist:
        profile = None
    try:
        kyc = author.kyc
    except AuthorKYC.DoesNotExist:
        kyc = None

    # Chapter breakdown
    chapters_qs = Chapter.objects.filter(story=story).order_by('chapter_number')
    chapter_stats = chapters_qs.aggregate(
        total=Count('id'),
        published=Count('id', filter=Q(is_published=True)),
        locked=Count('id', filter=Q(is_locked=True)),
        total_words=Sum('word_count'),
    )

    chapters_data = list(chapters_qs.values(
        'id', 'chapter_number', 'title', 'status', 'word_count',
        'is_published', 'is_locked', 'views', 'unlocks', 'created_at',
    ))

    # Reader metrics
    bookmarks       = Bookmark.objects.filter(story=story).count()
    active_readers  = ReadingProgress.objects.filter(story=story).count()
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
    recent_readers  = ReadingProgress.objects.filter(story=story, updated_at__gte=thirty_days_ago).count()

    # Top chapter by views
    top_chapter = chapters_qs.order_by('-views').first()

    # Platform rank by total_views (approx)
    rank = Story.objects.filter(total_views__gt=story.total_views).count() + 1

    # Contract application info
    from apps.editorial.models import ContractApplication
    try:
        app = story.contract_application
        contract_info = {
            'type': app.get_contract_type_display() if app.contract_type else None,
            'se_note': app.se_note,
            'sent_at': app.contract_sent_at.isoformat() if app.contract_sent_at else None,
            'signed_at': app.signed_at.isoformat() if app.signed_at else None,
        }
    except ContractApplication.DoesNotExist:
        contract_info = {}

    return Response({
        'story': {
            'title':             story.title,
            'slug':              story.slug,
            'status':            story.status,
            'contract_status':   story.contract_status,
            'lock_from_chapter': story.lock_from_chapter,
            'is_explicit':       story.is_explicit,
            'age_rating':        story.age_rating,
            'word_count':        story.word_count,
            'total_views':       story.total_views,
            'total_unlocks':     story.total_unlocks,
            'total_ratings':     story.total_ratings,
            'average_rating':    float(story.average_rating),
            'total_comments':    story.total_comments,
            'total_tips':        story.total_tips,
            'created_at':        story.created_at.isoformat(),
            'updated_at':        story.updated_at.isoformat(),
            'cover_image':       request.build_absolute_uri(story.cover_image.url) if story.cover_image else None,
            'rank_by_views':     rank,
            'is_editors_pick':          story.is_editors_pick,
            'editors_pick_expires_at':  story.editors_pick_expires_at.isoformat() if story.editors_pick_expires_at else None,
            'is_featured':              story.is_featured,
            'featured_expires_at':      story.featured_expires_at.isoformat() if story.featured_expires_at else None,
        },
        'chapters': {
            'total':     chapter_stats['total'] or 0,
            'published': chapter_stats['published'] or 0,
            'locked':    chapter_stats['locked'] or 0,
            'list':      chapters_data,
        },
        'readers': {
            'bookmarks':      bookmarks,
            'all_time':       active_readers,
            'last_30_days':   recent_readers,
            'top_chapter':    {
                'number': top_chapter.chapter_number,
                'title':  top_chapter.title,
                'views':  top_chapter.views,
                'unlocks': top_chapter.unlocks,
            } if top_chapter else None,
        },
        'author': {
            'username':       author.username,
            'full_name':      author.get_full_name(),
            'email':          author.email,
            'date_joined':    author.date_joined.isoformat(),
            'pen_name':       profile.pen_name if profile else '',
            'contract_type':  profile.get_contract_type_display() if profile else '',
            'contract_signed_at': profile.contract_signed_at.isoformat() if profile and profile.contract_signed_at else None,
            # Balance: only shown when SE-approved for the current month AND today >= 6th
            # earnings_pool = full 50% (author receives 25%; remaining 25% covers bonus pool + platform)
            'balance_visible':    profile.balance_is_visible() if profile else False,
            'earnings_pool':      round(float(profile.total_earnings) * 2, 2) if profile and profile.balance_is_visible() else None,
            'author_payout':      float(profile.total_earnings) if profile and profile.balance_is_visible() else None,
            'pending_payout':     float(profile.pending_payout) if profile and profile.balance_is_visible() else None,
            'completion_bonus':   float(profile.completion_bonus) if profile else 0,
            'balance_approved_at': profile.balance_approved_at.isoformat() if profile and profile.balance_approved_at else None,
            'balance_approved_by': profile.balance_approved_by.username if profile and profile.balance_approved_by else None,
            'kyc_status':     kyc.status if kyc else 'not_submitted',
            'kyc_full_name':  kyc.full_name if kyc else '',
            'kyc_country':    kyc.country if kyc else '',
        },
        'contract': contract_info,
    })


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_approve_author_balance(request, author_id):
    """POST /api/editorial/author-balance/<author_id>/approve/
    SE approves an author's balance to be visible for the current month.
    Can only be submitted on/after the 6th of the month.
    Body: {} (no body needed)
    """
    from apps.users.models import AuthorProfile
    from django.utils import timezone

    now = timezone.now()
    if now.day < 6:
        return Response(
            {'detail': 'Author balances can only be approved from the 6th of each month.'},
            status=400,
        )

    profile = get_object_or_404(
        AuthorProfile,
        user_id=author_id,
        user__editor_link__assigned_se=request.user,
    )

    profile.balance_approved_at = now
    profile.balance_approved_by = request.user
    profile.save(update_fields=['balance_approved_at', 'balance_approved_by'])

    return Response({
        'ok':              True,
        'author':          profile.user.username,
        'approved_at':     profile.balance_approved_at.isoformat(),
        'earnings_pool':   round(float(profile.total_earnings) * 2, 2),
        'author_payout':   float(profile.total_earnings),
        'pending_payout':  float(profile.pending_payout),
        'completion_bonus': float(profile.completion_bonus),
    })


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_award_completion_bonus(request, author_id):
    """POST /api/editorial/author-balance/<author_id>/award-bonus/
    SE/CE manually awards a completion bonus to an author.
    Body: { "amount": 150.00, "notes": "Completed 100-chapter milestone" }
    """
    from apps.users.models import AuthorProfile
    from decimal import Decimal, InvalidOperation

    raw = request.data.get('amount')
    try:
        amount = Decimal(str(raw))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError, InvalidOperation):
        return Response({'detail': 'A positive amount is required.'}, status=400)

    profile = get_object_or_404(AuthorProfile, user_id=author_id)
    profile.completion_bonus += amount
    profile.save(update_fields=['completion_bonus'])

    return Response({
        'ok':               True,
        'author':           profile.user.username,
        'amount_awarded':   float(amount),
        'completion_bonus': float(profile.completion_bonus),
        'notes':            request.data.get('notes', ''),
    })


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_set_lock_chapter(request, slug):
    """POST /api/editorial/story-queue/<slug>/set-lock/
    SE sets the chapter at which locking starts for a story.
    Body: { lock_from_chapter: 5 }  (null = unlock all)
    """
    from apps.stories.models import Story
    from apps.chapters.models import apply_lock_from_chapter

    story = get_object_or_404(
        Story,
        slug=slug,
        author__editor_link__assigned_se=request.user,
    )
    raw = request.data.get('lock_from_chapter')
    if raw is None or raw == '':
        lock_from = None
    else:
        try:
            lock_from = int(raw)
            if lock_from < 1:
                return Response({'detail': 'lock_from_chapter must be 1 or greater.'}, status=400)
        except (ValueError, TypeError):
            return Response({'detail': 'lock_from_chapter must be a positive integer or null.'}, status=400)

    story.lock_from_chapter = lock_from
    story.save(update_fields=['lock_from_chapter'])
    apply_lock_from_chapter(story)
    return Response({'ok': True, 'lock_from_chapter': lock_from})


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_set_story_explicit(request, slug):
    """POST /api/editorial/story-queue/<slug>/set-explicit/
    SE/CE classify a story's content.
    Body: { "is_explicit": true|false }
    Explicit stories are forced to the 18+ age rating. Visibility of
    explicit stories platform-wide is controlled by the PlatformSettings
    'show explicit content' switch.
    """
    from apps.stories.models import Story

    qs = Story.objects.all()
    # SEs may only classify their own authors' stories; CE/admin see all
    if getattr(request.user, 'role', '') == 'se' and not request.user.is_staff:
        qs = qs.filter(author__editor_link__assigned_se=request.user)
    story = get_object_or_404(qs, slug=slug)

    is_explicit = str(request.data.get('is_explicit')).lower() in ('1', 'true', 'yes', 'on')
    story.is_explicit = is_explicit
    if is_explicit:
        story.age_rating = '18+'
    story.save(update_fields=['is_explicit', 'age_rating'])
    return Response({'ok': True, 'is_explicit': story.is_explicit,
                     'age_rating': story.age_rating})


@api_view(['PATCH'])
@permission_classes([IsSEOrAbove])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def se_edit_story(request, slug):
    """PATCH /api/editorial/story-queue/<slug>/edit/
    SE edits story metadata: cover image, synopsis, description, outline, tags.
    Allowed on stories assigned to this SE (any contract status).
    """
    from apps.stories.models import Story, Tag
    import json as _json

    story = get_object_or_404(
        Story,
        slug=slug,
        author__editor_link__assigned_se=request.user,
    )

    for field in ('title', 'synopsis', 'story_outline',
                  'language', 'target_word_count', 'target_audience', 'external_link'):
        if field in request.data:
            setattr(story, field, request.data[field])

    if 'chapters_per_week' in request.data:
        try:
            val = int(request.data['chapters_per_week'])
            story.chapters_per_week = val if 1 <= val <= 7 else None
        except (TypeError, ValueError):
            story.chapters_per_week = None

    # SE-level promotion flags: editor's pick and featured
    import datetime as _dt
    try:
        promotion_days = max(1, min(90, int(request.data.get('promotion_days', 7))))
    except (TypeError, ValueError):
        promotion_days = 7

    se_promo_map = {
        'is_editors_pick': 'editors_pick_expires_at',
        'is_featured':     'featured_expires_at',
    }
    for bool_field, expiry_field in se_promo_map.items():
        if bool_field in request.data:
            enabled = str(request.data[bool_field]).lower() in ('true', '1', 'yes')
            setattr(story, bool_field, enabled)
            setattr(story, expiry_field,
                    timezone.now() + _dt.timedelta(days=promotion_days) if enabled else None)

    if 'cover_image' in request.FILES:
        import os
        img = request.FILES['cover_image']
        if img.size > 2 * 1024 * 1024:
            return Response({'detail': 'Cover image must be under 2MB.'}, status=400)
        ext = os.path.splitext(img.name)[1].lower() or '.jpg'
        img.name = f'story-{slug}{ext}'
        story.cover_image = img

    # tag_ids can come as a JSON string, a multi-value form list, or a single value
    if 'tag_ids' in request.data:
        # getlist handles MultiValueDict (multipart); falls back to list for JSON
        raw_list = request.data.getlist('tag_ids') if hasattr(request.data, 'getlist') else request.data.get('tag_ids')
        if isinstance(raw_list, str):
            try:
                tag_ids = _json.loads(raw_list)
            except ValueError:
                tag_ids = [raw_list]
        elif isinstance(raw_list, list):
            # Each item may itself be a JSON-encoded list (edge case)
            tag_ids = []
            for item in raw_list:
                if isinstance(item, str):
                    try:
                        parsed = _json.loads(item)
                        tag_ids += parsed if isinstance(parsed, list) else [parsed]
                    except ValueError:
                        tag_ids.append(item)
                else:
                    tag_ids.append(item)
        else:
            tag_ids = [raw_list] if raw_list is not None else []
        try:
            tag_ids = [int(t) for t in tag_ids]
        except (TypeError, ValueError):
            tag_ids = []
        story.tags.set(Tag.objects.filter(id__in=tag_ids))

    story.save()

    try:
        from apps.notifications.services import create_notification
        from apps.notifications.models import Notification
        create_notification(
            user=story.author,
            notification_type=Notification.TYPE_SYSTEM,
            title='Your story was updated',
            message=f'Your story "{story.title}" was edited by your SE ({request.user.get_full_name() or request.user.username}).',
            data={'slug': story.slug},
        )
    except Exception:
        pass

    return Response({
        'ok': True,
        'slug': story.slug,
        'cover_image': request.build_absolute_uri(story.cover_image.url) if story.cover_image else None,
    })


@api_view(['PATCH'])
@permission_classes([IsSEOrAbove])
@parser_classes([JSONParser, FormParser])
def se_edit_chapter(request, pk):
    """PATCH /api/editorial/chapters/<pk>/edit/
    SE edits a chapter title and/or content for an author assigned to them.
    """
    from apps.chapters.models import Chapter
    from re import sub as _sub

    chapter = get_object_or_404(
        Chapter,
        pk=pk,
        story__author__editor_link__assigned_se=request.user,
    )

    if 'title' in request.data:
        chapter.title = request.data['title']

    if 'content' in request.data:
        chapter.content = request.data['content']
        plain = _sub(r'<[^>]+>', ' ', chapter.content)
        chapter.word_count = len(plain.split())

    chapter.save()

    # Keep story word_count in sync
    from django.db.models import Sum
    total = chapter.story.chapters.aggregate(t=Sum('word_count'))['t'] or 0
    chapter.story.word_count = total
    chapter.story.save(update_fields=['word_count'])

    return Response({'ok': True, 'chapter_id': chapter.id, 'word_count': chapter.word_count})


# ── SE: author balance approvals ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSEOrAbove])
def se_author_balances(request):
    """GET /api/editorial/author-balances/
    SE views balance approval status for all their assigned authors.
    Balances (amounts) are only shown if already approved for this month.
    """
    from apps.users.models import AuthorProfile
    from django.utils import timezone

    now = timezone.now()
    from django.db.models import Q as _Q

    profiles = AuthorProfile.objects.filter(
        user__editor_link__assigned_se=request.user
    ).select_related('user', 'balance_approved_by')

    search = request.query_params.get('search', '').strip()
    if search:
        profiles = profiles.filter(
            _Q(user__username__icontains=search)
            | _Q(user__author_code__iexact=search)
            | _Q(pen_name__icontains=search)
        )

    results = []
    for p in profiles:
        visible = p.balance_is_visible()
        results.append({
            'author_id':         p.user_id,
            'author_code':       p.user.author_code or '',
            'username':          p.user.username,
            'pen_name':          p.pen_name,
            'balance_visible':   visible,
            'earnings_pool':     round(float(p.total_earnings) * 2, 2) if visible else None,
            'author_payout':     float(p.total_earnings) if visible else None,
            'pending_payout':    float(p.pending_payout) if visible else None,
            'completion_bonus':  float(p.completion_bonus),
            'balance_approved_at': p.balance_approved_at.isoformat() if p.balance_approved_at else None,
            'approved_this_month': (
                p.balance_approved_at is not None
                and p.balance_approved_at.year == now.year
                and p.balance_approved_at.month == now.month
            ),
            'can_approve_now':   now.day >= 6,
        })
    return Response({'count': len(results), 'results': results})


# ── SE: all assigned stories (for modals) ────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSEOrAbove])
def se_my_stories(request):
    """GET /api/editorial/my-stories/
    Returns all stories whose author is linked to this SE, regardless of status.
    Lightweight list used for flag / promotion modals.
    """
    from apps.stories.models import Story
    from django.db.models import Q

    qs = Story.objects.filter(
        author__editor_link__assigned_se=request.user,
    ).exclude(status=Story.STATUS_DRAFT)\
     .select_related('author')\
     .order_by('-updated_at')

    search = request.query_params.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(book_code__iexact=search)
            | Q(title__icontains=search)
            | Q(author__username__icontains=search)
            | Q(author__author_code__iexact=search)
        )

    data = list(qs.values('id', 'slug', 'book_code', 'title', 'contract_status'))
    return Response({'results': data})


# ── SE Content Flag submission ─────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_submit_flag(request):
    """POST /api/editorial/flags/
    SE submits a content flag on a chapter belonging to one of their linked authors.
    Body: { chapter_id, flag_type, description }
    """
    from apps.editorial.models import ContentFlag
    from apps.chapters.models import Chapter

    chapter_id  = request.data.get('chapter_id')
    flag_type   = request.data.get('flag_type', '').strip()
    description = request.data.get('description', '').strip()

    valid_types = {c[0] for c in ContentFlag.FLAG_CHOICES}
    if not chapter_id:
        return Response({'detail': 'chapter_id is required.'}, status=400)
    if flag_type not in valid_types:
        return Response({'detail': f'flag_type must be one of {sorted(valid_types)}.'}, status=400)
    if not description:
        return Response({'detail': 'description is required.'}, status=400)

    chapter = get_object_or_404(
        Chapter,
        pk=chapter_id,
        story__author__editor_link__assigned_se=request.user,
    )

    flag = ContentFlag.objects.create(
        chapter=chapter,
        flagged_by=request.user,
        flag_type=flag_type,
        description=description,
    )
    return Response({
        'ok':         True,
        'id':         flag.id,
        'flag_type':  flag.flag_type,
        'story_title': chapter.story.title,
        'chapter_num': chapter.chapter_number,
    }, status=201)


@api_view(['GET'])
@permission_classes([IsSEOrAbove])
def se_my_flags(request):
    """GET /api/editorial/flags/ — SE lists their own submitted flags."""
    from apps.editorial.models import ContentFlag
    qs = ContentFlag.objects.filter(flagged_by=request.user)\
                            .select_related('chapter__story')\
                            .order_by('-created_at')[:50]
    data = [{
        'id':           f.id,
        'flag_type':    f.flag_type,
        'description':  f.description,
        'chapter_id':   f.chapter_id,
        'chapter_num':  f.chapter.chapter_number if f.chapter else None,
        'story_title':  f.chapter.story.title if f.chapter and f.chapter.story else '—',
        'story_slug':   f.chapter.story.slug if f.chapter and f.chapter.story else None,
        'book_code':    f.chapter.story.book_code if f.chapter and f.chapter.story else None,
        'resolved':     f.resolved,
        'resolution_note': f.resolution_note,
        'created_at':   f.created_at.isoformat(),
    } for f in qs]
    return Response({'count': len(data), 'results': data})


# ── Tab / Section catalogue (mirrors ExploreTabView section slugs) ────────────

TAB_SECTIONS = {
    'werewolf': [
        {'slug': 'just-your-style',    'name': 'Just Your Style'},
        {'slug': 'fresh-reads',        'name': 'Fresh Reads'},
        {'slug': 'still-rolling-out',  'name': 'Still Rolling Out'},
        {'slug': 'short-fics',         'name': 'Dive into These Shorts'},
        {'slug': 'completed-classics', 'name': 'Completed Classics'},
    ],
    'billionaire': [
        {'slug': 'just-your-style',    'name': 'Just Your Style'},
        {'slug': 'fresh-reads',        'name': 'Fresh Reads'},
        {'slug': 'still-rolling-out',  'name': 'Still Rolling Out'},
        {'slug': 'short-fics',         'name': 'Dive into These Shorts'},
        {'slug': 'completed-classics', 'name': 'Completed Classics'},
    ],
    'suspense': [
        {'slug': 'editors-picks',     'name': "Editor's Picks"},
        {'slug': 'the-ends',          'name': 'The Ends'},
        {'slug': 'fresh-drops',       'name': 'Fresh Drops'},
        {'slug': 'trending-up',       'name': 'Trending Up'},
        {'slug': 'stars-of-tomorrow', 'name': 'Stars of Tomorrow'},
    ],
    'for-her': [
        {'slug': 'picks-for-you',      'name': 'Picks for You'},
        {'slug': 'fresh-releases',     'name': 'Fresh Releases'},
        {'slug': 'completed-classics', 'name': 'Completed Classics'},
    ],
    'for-him': [
        {'slug': 'picks-for-you',      'name': 'Picks for You'},
        {'slug': 'fresh-releases',     'name': 'Fresh Releases'},
        {'slug': 'completed-classics', 'name': 'Completed Classics'},
    ],
    'short-fics': [
        {'slug': 'romance',      'name': 'Romance'},
        {'slug': 'family-drama', 'name': 'Family Drama'},
        {'slug': 'reborn',       'name': 'Reborn / After Death'},
        {'slug': 'werewolf',     'name': "Werewolf's World"},
        {'slug': 'mafia',        'name': 'Mafia'},
        {'slug': 'revenge',      'name': 'Revenge'},
    ],
    'ranking': [
        {'slug': 'new-releases',  'name': 'New Releases'},
        {'slug': 'most-read',     'name': 'Most Read'},
        {'slug': 'short-stories', 'name': 'Short Stories'},
    ],
}


class TabSectionsView(APIView):
    """GET /api/editorial/tab-sections/
    Returns available tabs and their pinnable sections.
    Used by SE modal and mobile app to populate dropdowns.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'tabs': [
                {
                    'slug': tab,
                    'name': tab.replace('-', ' ').title(),
                    'sections': sections,
                }
                for tab, sections in TAB_SECTIONS.items()
            ]
        })


# ── SE Promotion Request submission ───────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsSEOrAbove])
def se_promotion_requests(request):
    """
    GET  /api/editorial/promotion-requests/  — SE lists their own promotion requests.
    POST /api/editorial/promotion-requests/  — SE submits a new one.
         Body: { story_slug, tab, section, message }
         tab:     werewolf | billionaire | short-fics | ranking | for-her | for-him | suspense
         section: valid slug for the chosen tab (see /api/editorial/tab-sections/)
    """
    from apps.editorial.models import SEPromotionRequest
    from apps.stories.models import Story

    VALID_TABS = set(TAB_SECTIONS.keys())

    if request.method == 'GET':
        qs = SEPromotionRequest.objects.filter(se=request.user)\
                                       .select_related('story', 'reviewed_by')\
                                       .order_by('-created_at')
        data = [{
            'id':          r.id,
            'story_title': r.story.title,
            'story_slug':  r.story.slug,
            'book_code':   r.story.book_code,
            'tab':         r.tab,
            'section':     r.section,
            'message':     r.message,
            'status':      r.status,
            'ce_note':     r.ce_note,
            'created_at':  r.created_at.isoformat(),
            'reviewed_at': r.reviewed_at.isoformat() if r.reviewed_at else None,
            'reviewed_by': r.reviewed_by.username if r.reviewed_by else None,
        } for r in qs]
        return Response({'count': len(data), 'results': data})

    # POST
    slug    = request.data.get('story_slug', '').strip()
    tab     = request.data.get('tab', '').strip()
    section = request.data.get('section', '').strip()
    message = request.data.get('message', '').strip()

    if not slug:
        return Response({'detail': 'story_slug is required.'}, status=400)
    if not tab or tab not in VALID_TABS:
        return Response({'detail': f'tab must be one of: {", ".join(sorted(VALID_TABS))}'}, status=400)
    valid_sections = {s['slug'] for s in TAB_SECTIONS[tab]}
    if not section or section not in valid_sections:
        return Response({
            'detail': f'section must be one of: {", ".join(s["slug"] for s in TAB_SECTIONS[tab])}'
        }, status=400)
    if not message:
        return Response({'detail': 'message is required.'}, status=400)

    story = get_object_or_404(
        Story,
        slug=slug,
        author__editor_link__assigned_se=request.user,
    )

    if SEPromotionRequest.objects.filter(
        se=request.user, story=story, tab=tab, section=section, status='pending'
    ).exists():
        return Response({'detail': 'A pending promotion request for this story/section already exists.'}, status=400)

    req = SEPromotionRequest.objects.create(
        se=request.user,
        story=story,
        tab=tab,
        section=section,
        message=message,
    )
    return Response({
        'ok':          True,
        'id':          req.id,
        'story_title': story.title,
        'tab':         req.tab,
        'section':     req.section,
        'status':      req.status,
    }, status=201)


@api_view(['PATCH'])
@permission_classes([IsCE])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def ce_edit_story(request, slug):
    """PATCH /api/editorial/ce-story-queue/<slug>/edit/
    CE edits story metadata and boolean flags. CE can access any contracted/signed story.
    """
    from apps.stories.models import Story, Tag
    import json as _json, os as _os, datetime

    story = get_object_or_404(Story, slug=slug)

    for field in ('title', 'synopsis', 'story_outline', 'language',
                  'target_word_count', 'target_audience', 'external_link'):
        if field in request.data:
            setattr(story, field, request.data[field])

    if 'chapters_per_week' in request.data:
        try:
            val = int(request.data['chapters_per_week'])
            story.chapters_per_week = val if 1 <= val <= 7 else None
        except (TypeError, ValueError):
            story.chapters_per_week = None

    # CE-only: set/clear timed promotion section flags
    promo_map = {
        'is_editors_pick':     'editors_pick_expires_at',
        'is_world_famous':     'world_famous_expires_at',
        'is_african_folktale': 'african_folktale_expires_at',
        'is_featured':         'featured_expires_at',
        'is_free_download':    'free_download_expires_at',
    }
    try:
        promotion_days = max(1, min(90, int(request.data.get('promotion_days', 7))))
    except (TypeError, ValueError):
        promotion_days = 7

    for bool_field, expiry_field in promo_map.items():
        if bool_field in request.data:
            enabled = str(request.data[bool_field]).lower() in ('true', '1', 'yes')
            setattr(story, bool_field, enabled)
            if enabled:
                setattr(story, expiry_field, timezone.now() + datetime.timedelta(days=promotion_days))
            else:
                setattr(story, expiry_field, None)

    if 'cover_image' in request.FILES:
        img = request.FILES['cover_image']
        if img.size > 2 * 1024 * 1024:
            return Response({'detail': 'Cover image must be under 2MB.'}, status=400)
        ext = _os.path.splitext(img.name)[1].lower() or '.jpg'
        img.name = f'story-{slug}{ext}'
        story.cover_image = img

    if 'tag_ids' in request.data:
        raw_list = request.data.getlist('tag_ids') if hasattr(request.data, 'getlist') else request.data.get('tag_ids')
        if isinstance(raw_list, str):
            try:
                tag_ids = _json.loads(raw_list)
            except ValueError:
                tag_ids = [raw_list]
        elif isinstance(raw_list, list):
            tag_ids = []
            for item in raw_list:
                if isinstance(item, str):
                    try:
                        parsed = _json.loads(item)
                        tag_ids += parsed if isinstance(parsed, list) else [parsed]
                    except ValueError:
                        tag_ids.append(item)
                else:
                    tag_ids.append(item)
        else:
            tag_ids = [raw_list] if raw_list is not None else []
        try:
            tag_ids = [int(t) for t in tag_ids]
        except (TypeError, ValueError):
            tag_ids = []
        story.tags.set(Tag.objects.filter(id__in=tag_ids))

    story.save()

    return Response({
        'ok': True,
        'slug': story.slug,
        'cover_image': request.build_absolute_uri(story.cover_image.url) if story.cover_image else None,
    })


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_mark_story_complete(request, slug):
    """POST /api/editorial/story-queue/<slug>/mark-complete/  — SE marks a signed story as completed."""
    from apps.stories.models import Story
    story = get_object_or_404(
        Story,
        slug=slug,
        contract_status='signed',
        author__editor_link__assigned_se=request.user,
    )
    story.status = Story.STATUS_COMPLETED
    story.save(update_fields=['status'])
    return Response({'ok': True, 'status': story.status})


# ─── CE Account Moderation ────────────────────────────────────────────────────

class CEUserSearchView(APIView):
    """GET /api/editorial/ce/users/?q=<search>
    Search users by username or email (CE only)."""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.users.models import User as _User
        from django.db.models import Q
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({'results': []})
        qs = _User.objects.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(author_code__iexact=q)
        ).order_by('username')[:50]
        return Response({'results': [_user_summary(u) for u in qs]})


def _user_summary(u):
    return {
        'id':              u.id,
        'author_code':     u.author_code or '',
        'username':        u.username,
        'email':           u.email,
        'role':            u.role,
        'registration_ip': u.registration_ip,
        'is_active':       u.is_active,
        'is_banned':       u.is_banned,
        'ban_reason':      u.ban_reason,
        'date_joined':     u.date_joined.isoformat(),
    }


class CESuspiciousAccountsView(APIView):
    """GET /api/editorial/ce/suspicious-accounts/
    Returns groups of accounts that share a registration IP or a device ID.
    Query params: ?mode=ip (default) | ?mode=device
    """
    permission_classes = [IsCE]

    def get(self, request):
        from django.db.models import Count
        from apps.users.models import User as _User, UserDevice

        mode = request.query_params.get('mode', 'ip')

        if mode == 'device':
            # Group by device_id — find devices used by more than one account
            dup_devices = (
                UserDevice.objects.values('device_id')
                .annotate(cnt=Count('user_id', distinct=True))
                .filter(cnt__gt=1)
                .order_by('-cnt')
            )
            groups = []
            for row in dup_devices:
                device_id = row['device_id']
                user_ids  = UserDevice.objects.filter(device_id=device_id).values_list('user_id', flat=True)
                users     = _User.objects.filter(pk__in=user_ids).order_by('date_joined')
                platform  = UserDevice.objects.filter(device_id=device_id).values_list('platform', flat=True).first() or ''
                groups.append({
                    'device_id': device_id,
                    'platform':  platform,
                    'count':     row['cnt'],
                    'accounts':  [_user_summary(u) for u in users],
                })
            return Response({'mode': 'device', 'count': len(groups), 'results': groups})

        # Default: group by IP
        dup_ips = (
            _User.objects.exclude(registration_ip=None)
            .values('registration_ip')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
            .values_list('registration_ip', flat=True)
        )

        groups = []
        for ip in dup_ips:
            users = _User.objects.filter(registration_ip=ip).order_by('date_joined')
            groups.append({
                'ip':       ip,
                'count':    users.count(),
                'accounts': [_user_summary(u) for u in users],
            })

        groups.sort(key=lambda g: g['count'], reverse=True)
        return Response({'mode': 'ip', 'count': len(groups), 'results': groups})


class CEIPAccountsView(APIView):
    """GET /api/editorial/ce/ip-accounts/<ip>/
    All accounts registered from a specific IP."""
    permission_classes = [IsCE]

    def get(self, request, ip):
        from apps.users.models import User as _User
        users = _User.objects.filter(registration_ip=ip).order_by('date_joined')
        return Response({
            'ip':       ip,
            'count':    users.count(),
            'accounts': [_user_summary(u) for u in users],
        })


class CEDeviceAccountsView(APIView):
    """GET /api/editorial/ce/device-accounts/<device_id>/
    All accounts that have logged in from a specific device ID."""
    permission_classes = [IsCE]

    def get(self, request, device_id):
        from apps.users.models import UserDevice, User as _User
        entries  = UserDevice.objects.filter(device_id=device_id).select_related('user').order_by('first_seen')
        users    = [e.user for e in entries]
        platform = entries.first().platform if entries.exists() else ''
        return Response({
            'device_id': device_id,
            'platform':  platform,
            'count':     len(users),
            'accounts':  [_user_summary(u) for u in users],
        })


@api_view(['POST'])
@permission_classes([IsCE])
def ce_ban_user(request, pk):
    """POST /api/editorial/ce/users/<pk>/ban/
    Body: { "reason": "..." }
    Bans the user and disables login."""
    from apps.users.models import User as _User
    user = get_object_or_404(_User, pk=pk)
    if user.role in ('ce', 'se'):
        return Response({'detail': 'Cannot ban editorial staff.'}, status=403)

    reason = request.data.get('reason', '').strip()
    user.is_banned  = True
    user.is_active  = False
    user.ban_reason = reason
    user.save(update_fields=['is_banned', 'is_active', 'ban_reason'])
    return Response({'detail': f'User {user.username} has been banned.', 'user': _user_summary(user)})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_unban_user(request, pk):
    """POST /api/editorial/ce/users/<pk>/unban/"""
    from apps.users.models import User as _User
    user = get_object_or_404(_User, pk=pk)
    user.is_banned  = False
    user.is_active  = True
    user.ban_reason = ''
    user.save(update_fields=['is_banned', 'is_active', 'ban_reason'])
    return Response({'detail': f'User {user.username} has been unbanned.', 'user': _user_summary(user)})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_disable_user(request, pk):
    """POST /api/editorial/ce/users/<pk>/disable/
    Disables login without a full ban (reversible)."""
    from apps.users.models import User as _User
    user = get_object_or_404(_User, pk=pk)
    if user.role in ('ce', 'se'):
        return Response({'detail': 'Cannot disable editorial staff.'}, status=403)
    user.is_active = False
    user.save(update_fields=['is_active'])
    return Response({'detail': f'Account {user.username} disabled.', 'user': _user_summary(user)})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_enable_user(request, pk):
    """POST /api/editorial/ce/users/<pk>/enable/"""
    from apps.users.models import User as _User
    user = get_object_or_404(_User, pk=pk)
    if user.is_banned:
        return Response({'detail': 'User is banned. Use /unban/ to restore.'}, status=400)
    user.is_active = True
    user.save(update_fields=['is_active'])
    return Response({'detail': f'Account {user.username} enabled.', 'user': _user_summary(user)})


class CEBlacklistedIPListView(APIView):
    """GET  /api/editorial/ce/blacklisted-ips/ — list all blacklisted IPs.
    POST /api/editorial/ce/blacklisted-ips/ — blacklist an IP.
    Body: { "ip_address": "1.2.3.4", "reason": "...", "ban_existing": true }
    ban_existing=true also bans all accounts registered from that IP."""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.users.models import BlacklistedIP
        qs = BlacklistedIP.objects.select_related('blacklisted_by').order_by('-created_at')
        data = [
            {
                'id':             b.id,
                'ip_address':     b.ip_address,
                'reason':         b.reason,
                'blacklisted_by': b.blacklisted_by.username if b.blacklisted_by else None,
                'created_at':     b.created_at.isoformat(),
            }
            for b in qs
        ]
        return Response({'count': len(data), 'results': data})

    def post(self, request):
        from apps.users.models import BlacklistedIP, User as _User
        ip      = request.data.get('ip_address', '').strip()
        reason  = request.data.get('reason', '').strip()
        ban_existing = request.data.get('ban_existing', False)

        if not ip:
            return Response({'detail': 'ip_address is required.'}, status=400)

        entry, created = BlacklistedIP.objects.get_or_create(
            ip_address=ip,
            defaults={'reason': reason, 'blacklisted_by': request.user},
        )
        if not created:
            entry.reason = reason
            entry.save(update_fields=['reason'])

        banned_count = 0
        if ban_existing:
            affected = _User.objects.filter(registration_ip=ip, is_banned=False).exclude(role__in=['ce', 'se'])
            banned_count = affected.update(is_banned=True, is_active=False, ban_reason=f'IP blacklisted: {reason}')

        return Response({
            'detail':        f'IP {ip} blacklisted.',
            'banned_accounts': banned_count,
        }, status=201 if created else 200)


@api_view(['DELETE'])
@permission_classes([IsCE])
def ce_remove_blacklisted_ip(request, pk):
    """DELETE /api/editorial/ce/blacklisted-ips/<pk>/"""
    from apps.users.models import BlacklistedIP
    entry = get_object_or_404(BlacklistedIP, pk=pk)
    ip = entry.ip_address
    entry.delete()
    return Response({'detail': f'IP {ip} removed from blacklist.'})


# ═══════════════════════════════════════════════════════════════════════════════
# CE DASHBOARD — Extended Features
# ═══════════════════════════════════════════════════════════════════════════════

# ── Dashboard Stats ────────────────────────────────────────────────────────────

class CEDashboardStatsView(APIView):
    """GET /api/editorial/ce/dashboard-stats/"""
    permission_classes = [IsCE]

    def get(self, request):
        from datetime import timedelta, date
        from django.db.models import Count, Sum, Q
        from apps.users.models import User as _User
        from apps.stories.models import Story
        from apps.chapters.models import Chapter
        from apps.coins.models import Purchase

        now   = date.today()
        m_ago = now - timedelta(days=30)

        active_ses   = _User.objects.filter(role='se', is_active=True).count()
        total_authors= _User.objects.filter(role='author', is_active=True).count()
        new_users_30 = _User.objects.filter(date_joined__date__gte=m_ago).count()
        new_stories_30 = Story.objects.filter(created_at__date__gte=m_ago).count()
        new_chapters_30= Chapter.objects.filter(created_at__date__gte=m_ago, is_published=True).count()
        total_revenue = Purchase.objects.filter(status='completed').aggregate(t=Sum('amount_paid_usd'))['t'] or 0
        revenue_30    = Purchase.objects.filter(status='completed', completed_at__date__gte=m_ago).aggregate(t=Sum('amount_paid_usd'))['t'] or 0
        contracted_books = Story.objects.filter(contract_status='signed').count()

        # Monthly growth (last 6 months)
        monthly = []
        for i in range(5, -1, -1):
            import calendar as cal
            from datetime import datetime
            dt = datetime(now.year, now.month, 1) - timedelta(days=i * 28)
            y, m = dt.year, dt.month
            label = dt.strftime('%b %Y')
            u_count = _User.objects.filter(date_joined__year=y, date_joined__month=m).count()
            s_count = Story.objects.filter(created_at__year=y, created_at__month=m).count()
            monthly.append({'label': label, 'users': u_count, 'stories': s_count})

        # Top 5 books by views
        top_books = list(
            Story.objects.order_by('-total_views').select_related('author')[:5]
            .values('slug', 'title', 'total_views', 'total_chapters', 'cover_image',
                    'author__username', 'status', 'contract_status')
        )

        # Top 5 authors by earnings
        from apps.users.models import AuthorProfile
        top_authors = list(
            AuthorProfile.objects.select_related('user')
            .order_by('-total_earnings')[:5]
            .values('user__id', 'user__username', 'total_earnings', 'pending_payout', 'has_contract')
        )

        return Response({
            'active_ses':      active_ses,
            'total_authors':   total_authors,
            'new_users_30':    new_users_30,
            'new_stories_30':  new_stories_30,
            'new_chapters_30': new_chapters_30,
            'total_revenue':   float(total_revenue),
            'revenue_30':      float(revenue_30),
            'contracted_books': contracted_books,
            'monthly_growth':  monthly,
            'top_books':       top_books,
            'top_authors':     top_authors,
        })


# ── SE Performance ─────────────────────────────────────────────────────────────

class CESEPerformanceView(APIView):
    """GET /api/editorial/ce/se-performance/"""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.users.models import User as _User
        from apps.stories.models import Story
        from apps.editorial.models import ContractApplication, AuthorEditorLink as AEL

        from apps.users.models import AuthorProfile
        from django.db.models import Sum, Avg as DAvg

        ses = _User.objects.filter(role='se', is_active=True).order_by('username')
        result = []
        for se in ses:
            author_ids = list(AEL.objects.filter(assigned_se=se).values_list('author_id', flat=True))
            total_authors    = len(author_ids)
            contracted_books = Story.objects.filter(
                author_id__in=author_ids, contract_status='signed'
            ).count()
            total_stories    = Story.objects.filter(author_id__in=author_ids).count()
            pending_apps     = ContractApplication.objects.filter(
                assigned_se=se, status__in=['pending', 'se_reviewing']
            ).count()
            promotion_reqs   = se.promotion_requests.filter(status='pending').count()

            # Earnings & performance of SE's author roster
            earnings_agg = AuthorProfile.objects.filter(user_id__in=author_ids).aggregate(
                total=Sum('total_earnings'),
                pending=Sum('pending_payout'),
            )
            author_earnings_total   = float(earnings_agg['total'] or 0)
            author_earnings_pending = float(earnings_agg['pending'] or 0)

            # Story performance across the SE's roster
            story_perf = Story.objects.filter(author_id__in=author_ids).aggregate(
                total_views=Sum('total_views'),
                total_unlocks=Sum('total_unlocks'),
                avg_rating=DAvg('average_rating'),
            )

            result.append({
                'id':               se.id,
                'username':         se.username,
                'display_name':     se.get_full_name() or se.username,
                'email':            se.email,
                'is_active':        se.is_active,
                # Roster
                'total_authors':    total_authors,
                'total_stories':    total_stories,
                'contracted_books': contracted_books,
                # Queue
                'pending_reviews':  pending_apps,
                'promotion_reqs':   promotion_reqs,
                # Earnings (50% pool visible to CE)
                'earnings_pool':    round(author_earnings_total * 2, 2),
                'author_payout':    author_earnings_total,
                'earnings_pending': round(author_earnings_pending * 2, 2),
                # Performance
                'total_views':      story_perf['total_views'] or 0,
                'total_unlocks':    story_perf['total_unlocks'] or 0,
                'avg_rating':       round(float(story_perf['avg_rating'] or 0), 2),
            })

        sort_by = request.query_params.get('sort', 'contracted_books')
        reverse = request.query_params.get('order', 'desc') != 'asc'
        if sort_by in ('contracted_books', 'total_authors', 'earnings_pool', 'total_views', 'avg_rating'):
            result.sort(key=lambda x: x[sort_by], reverse=reverse)

        return Response({'count': len(result), 'results': result})


# ── Books Browser ──────────────────────────────────────────────────────────────

class CEBooksView(APIView):
    """GET /api/editorial/ce/books/?status=&search=&page="""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.stories.models import Story
        from django.db.models import Q

        qs = Story.objects.select_related('author', 'genre').prefetch_related('tags')
        status = request.query_params.get('status', '')
        search = request.query_params.get('search', '')
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(book_code__iexact=search)
                | Q(title__icontains=search)
                | Q(author__username__icontains=search)
                | Q(author__author_code__iexact=search)
            )

        sort_by = request.query_params.get('sort', 'views')
        sort_map = {
            'views':    '-total_views',
            'earnings': '-author__author_profile__total_earnings',
            'unlocks':  '-total_unlocks',
            'chapters': '-total_chapters',
            'rating':   '-average_rating',
            'recent':   '-created_at',
        }
        qs = qs.order_by(sort_map.get(sort_by, '-total_views'))

        page     = max(1, int(request.query_params.get('page', 1)))
        per_page = 20
        total    = qs.count()
        stories  = qs.select_related(
            'author__author_profile', 'author__editor_link__assigned_se', 'genre'
        )[(page - 1) * per_page: page * per_page]

        data = []
        for s in stories:
            se_name = ''
            try:
                link    = s.author.editor_link
                se_name = link.assigned_se.username if link.assigned_se else ''
            except Exception:
                pass

            # Estimated coin revenue: unlocks × average coin cost per chapter
            try:
                avg_coin_cost = s.chapters.filter(is_locked=True).aggregate(
                    avg=models.Avg('coin_cost')
                )['avg'] or 0
                coin_revenue_est = round(float(s.total_unlocks * avg_coin_cost), 2)
            except Exception:
                coin_revenue_est = 0

            try:
                author_earnings = float(s.author.author_profile.total_earnings)
            except Exception:
                author_earnings = 0

            data.append({
                'id':               s.id,
                'slug':             s.slug,
                'book_code':        s.book_code,
                'title':            s.title,
                'cover_image':      request.build_absolute_uri(s.cover_image.url) if s.cover_image else None,
                'author':           s.author.username,
                'author_id':        s.author.id,
                'author_code':      s.author.author_code or '',
                'genre':            s.genre.name if s.genre else '',
                'se':               se_name,
                'status':           s.status,
                'contract_status':  s.contract_status,
                'total_views':      s.total_views,
                'total_chapters':   s.total_chapters,
                'total_unlocks':    s.total_unlocks,
                'total_comments':   s.total_comments,
                'average_rating':   float(s.average_rating),
                'word_count':       s.word_count,
                'coin_revenue_est': coin_revenue_est,
                'author_earnings':  author_earnings,
                'created_at':       s.created_at.isoformat(),
                'published_at':     s.published_at.isoformat() if s.published_at else None,
            })

        return Response({'total': total, 'page': page, 'results': data})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_remove_story(request, slug):
    """POST /api/editorial/ce/books/<slug>/remove/ — marks story as rejected/removed."""
    from apps.stories.models import Story
    story  = get_object_or_404(Story, slug=slug)
    reason = request.data.get('reason', '')
    story.status = 'rejected'
    story.save(update_fields=['status'])
    return Response({'detail': f'Story "{story.title}" removed.', 'slug': slug})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_restore_story(request, slug):
    """POST /api/editorial/ce/books/<slug>/restore/"""
    from apps.stories.models import Story
    story = get_object_or_404(Story, slug=slug)
    story.status = 'ongoing'
    story.save(update_fields=['status'])
    return Response({'detail': f'Story "{story.title}" restored.', 'slug': slug})


# ── Contracts ─────────────────────────────────────────────────────────────────

class CEContractsView(APIView):
    """GET /api/editorial/ce/contracts/?status="""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.editorial.models import ContractApplication
        from django.db.models import Q

        status = request.query_params.get('status', '')
        search = request.query_params.get('search', '').strip()
        qs = ContractApplication.objects.select_related('story', 'author', 'assigned_se', 'ce_signed_by')
        if status:
            qs = qs.filter(status=status)
        else:
            qs = qs.order_by('-applied_at')
        if search:
            qs = qs.filter(
                Q(story__book_code__iexact=search)
                | Q(story__title__icontains=search)
                | Q(author__username__icontains=search)
                | Q(author__author_code__iexact=search)
            )

        data = [{
            'id':               c.id,
            'story_slug':       c.story.slug,
            'book_code':        c.story.book_code,
            'story_title':      c.story.title,
            'cover_image':      request.build_absolute_uri(c.story.cover_image.url) if c.story.cover_image else None,
            'author':           c.author.username,
            'author_id':        c.author.id,
            'author_code':      c.author.author_code or '',
            'se':               c.assigned_se.username if c.assigned_se else '—',
            'status':           c.status,
            'contract_type':    c.contract_type,
            'applied_at':       c.applied_at.isoformat(),
            'signed_at':        c.signed_at.isoformat() if c.signed_at else None,
            'rejected_at':      c.rejected_at.isoformat() if c.rejected_at else None,
            'rejection_reason': c.rejection_reason,
            'ce_signed_by':     c.ce_signed_by.username if c.ce_signed_by else None,
        } for c in qs]

        return Response({'count': len(data), 'results': data})


# ── Revenue & Payouts ─────────────────────────────────────────────────────────

class CERevenueView(APIView):
    """GET /api/editorial/ce/revenue/"""
    permission_classes = [IsCE]

    def get(self, request):
        from datetime import timedelta, date, datetime
        from django.db.models import Sum, Count
        from apps.coins.models import Purchase, AuthorPayout
        from apps.users.models import AuthorProfile

        now = date.today()

        # Monthly revenue — last 6 months
        monthly_rev = []
        for i in range(5, -1, -1):
            dt  = datetime(now.year, now.month, 1) - timedelta(days=i * 28)
            y, m = dt.year, dt.month
            rev = Purchase.objects.filter(
                status='completed', completed_at__year=y, completed_at__month=m
            ).aggregate(t=Sum('amount_paid_usd'))['t'] or 0
            monthly_rev.append({'label': dt.strftime('%b %Y'), 'revenue': float(rev)})

        total_revenue   = Purchase.objects.filter(status='completed').aggregate(t=Sum('amount_paid_usd'))['t'] or 0
        coin_revenue    = Purchase.objects.filter(status='completed', purchase_type='coin_pack').aggregate(t=Sum('amount_paid_usd'))['t'] or 0
        sub_revenue     = Purchase.objects.filter(status='completed', purchase_type='subscription').aggregate(t=Sum('amount_paid_usd'))['t'] or 0

        # Author earnings — pool = 50% (stored value is 25% author share; platform holds 2x)
        author_agg = AuthorProfile.objects.aggregate(
            total=Sum('total_earnings'),
            pending=Sum('pending_payout'),
            bonus=Sum('completion_bonus'),
        )
        author_total   = float(author_agg['total'] or 0)
        author_pending = float(author_agg['pending'] or 0)
        bonus_total    = float(author_agg['bonus'] or 0)

        # Top 10 earners
        top_earners_qs = list(
            AuthorProfile.objects.select_related('user')
            .order_by('-total_earnings')[:10]
            .values('user__id', 'user__username', 'total_earnings', 'pending_payout',
                    'completion_bonus', 'contract_type')
        )
        top_earners = [
            {
                **e,
                'earnings_pool': round(float(e['total_earnings']) * 2, 2),
                'author_payout': float(e['total_earnings']),
                'pending_payout': float(e['pending_payout']),
                'completion_bonus': float(e['completion_bonus']),
            }
            for e in top_earners_qs
        ]

        # Pending payouts
        pending_payouts = list(
            AuthorPayout.objects.filter(status='pending')
            .select_related('author')
            .order_by('-requested_at')[:50]
            .values('id', 'author__id', 'author__username', 'amount_usd', 'coins_total',
                    'payout_method', 'requested_at', 'notes')
        )

        return Response({
            'total_revenue':        float(total_revenue),
            'coin_revenue':         float(coin_revenue),
            'sub_revenue':          float(sub_revenue),
            # earnings_pool = full 50% visible to CE; author_payout = 25% paid out
            'earnings_pool_total':   round(author_total * 2, 2),
            'author_payout_total':   author_total,
            'earnings_pool_pending': round(author_pending * 2, 2),
            'author_payout_pending': author_pending,
            'completion_bonus_total': bonus_total,
            'monthly_revenue':       monthly_rev,
            'top_earners':           top_earners,
            'pending_payouts':       pending_payouts,
        })


class CEAuthorBalancesView(APIView):
    """GET /api/editorial/ce/author-balances/
    CE views all author balances.
    ?approved_only=true  — only show SE-approved for current month
    Only returns balance fields where balance_is_visible() is True, unless
    the CE explicitly requests all (?show_all=true).
    """
    permission_classes = [IsCE]

    def get(self, request):
        from apps.users.models import AuthorProfile
        from django.utils import timezone

        qs = AuthorProfile.objects.select_related(
            'user', 'balance_approved_by'
        ).order_by('-total_earnings')

        results = []
        for p in qs:
            visible = p.balance_is_visible()
            show_all = request.query_params.get('show_all', '').lower() == 'true'
            if request.query_params.get('approved_only', '').lower() == 'true' and not visible:
                continue
            results.append({
                'author_id':         p.user_id,
                'username':          p.user.username,
                'balance_visible':   visible,
                'earnings_pool':     round(float(p.total_earnings) * 2, 2) if visible or show_all else None,
                'author_payout':     float(p.total_earnings) if visible or show_all else None,
                'pending_payout':    float(p.pending_payout) if visible or show_all else None,
                'completion_bonus':  float(p.completion_bonus),
                'balance_approved_at': p.balance_approved_at.isoformat() if p.balance_approved_at else None,
                'balance_approved_by': p.balance_approved_by.username if p.balance_approved_by else None,
            })
        return Response({'count': len(results), 'results': results})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_process_payout(request, pk):
    """POST /api/editorial/ce/payouts/<pk>/process/  — mark payout as processed."""
    from apps.coins.models import AuthorPayout
    from django.utils import timezone
    payout = get_object_or_404(AuthorPayout, pk=pk)
    payout.status = AuthorPayout.STATUS_PROCESSED
    payout.processed_at = timezone.now()
    payout.notes = request.data.get('notes', payout.notes)
    payout.save(update_fields=['status', 'processed_at', 'notes'])
    return Response({'detail': 'Payout marked as processed.'})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_reject_payout(request, pk):
    """POST /api/editorial/ce/payouts/<pk>/reject/"""
    from apps.coins.models import AuthorPayout
    payout = get_object_or_404(AuthorPayout, pk=pk)
    payout.status = AuthorPayout.STATUS_FAILED
    payout.notes = request.data.get('notes', payout.notes)
    payout.save(update_fields=['status', 'notes'])
    return Response({'detail': 'Payout rejected.'})


# ── Platform Analytics ─────────────────────────────────────────────────────────

class CEAnalyticsView(APIView):
    """GET /api/editorial/ce/analytics/"""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.stories.models import Story, Genre
        from apps.users.models import User as _User
        from apps.chapters.models import Chapter
        from django.db.models import Count, Sum, Avg

        # Top 10 books (ongoing or completed — exclude drafts/paused)
        top_books = list(
            Story.objects.filter(status__in=['ongoing', 'completed']).order_by('-total_views')[:10]
            .values('slug', 'title', 'total_views', 'total_chapters', 'total_comments',
                    'average_rating', 'author__username', 'cover_image')
        )

        # Genre popularity (number of stories per genre)
        genre_stats = list(
            Genre.objects.annotate(story_count=Count('stories')).order_by('-story_count')[:10]
            .values('name', 'story_count')
        )

        # Completion rate
        total_stories    = Story.objects.count()
        completed_stories= Story.objects.filter(status='completed').count()
        ongoing_stories  = Story.objects.filter(status='ongoing').count()

        # Reader stats
        total_users    = _User.objects.filter(role='reader').count()
        total_bookmarks= __import__('apps.stories.models', fromlist=['Bookmark']).Bookmark.objects.count()

        # Country distribution — use registration metadata if available
        country_data = list(
            _User.objects.exclude(country='').values('country')
            .annotate(cnt=Count('id')).order_by('-cnt')[:15]
        ) if hasattr(_User, 'country') else []

        return Response({
            'top_books':         top_books,
            'genre_stats':       genre_stats,
            'total_stories':     total_stories,
            'completed_stories': completed_stories,
            'ongoing_stories':   ongoing_stories,
            'total_users':       total_users,
            'total_bookmarks':   total_bookmarks,
            'country_data':      country_data,
        })


# ── Visitor Analytics ──────────────────────────────────────────────────────────

class CEVisitorAnalyticsView(APIView):
    """GET /api/editorial/ce/visitor-analytics/?days=30"""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.analytics.models import PageVisit
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta

        try:
            days = max(1, min(int(request.query_params.get('days', 30)), 365))
        except (ValueError, TypeError):
            days = 30

        since = timezone.now() - timedelta(days=days)
        qs = PageVisit.objects.filter(created_at__gte=since)

        # Total visits
        total_visits = qs.count()

        # Unique IPs
        unique_visitors = qs.exclude(ip_address__isnull=True)\
                            .values('ip_address').distinct().count()

        # By country (top 20)
        by_country = list(
            qs.exclude(country='')
              .values('country', 'country_code')
              .annotate(visits=Count('id'))
              .order_by('-visits')[:20]
        )

        # By device type
        by_device = list(
            qs.exclude(device_type='')
              .values('device_type')
              .annotate(visits=Count('id'))
              .order_by('-visits')
        )

        # By browser (top 10)
        by_browser = list(
            qs.exclude(browser='')
              .values('browser')
              .annotate(visits=Count('id'))
              .order_by('-visits')[:10]
        )

        # By OS (top 10)
        by_os = list(
            qs.exclude(os='')
              .values('os')
              .annotate(visits=Count('id'))
              .order_by('-visits')[:10]
        )

        # Daily trend (last `days` days, grouped by date)
        from django.db.models.functions import TruncDate
        daily = list(
            qs.annotate(date=TruncDate('created_at'))
              .values('date')
              .annotate(visits=Count('id'))
              .order_by('date')
        )
        daily_trend = [{'date': str(d['date']), 'visits': d['visits']} for d in daily]

        # Top pages (top 20, exclude pure API calls if desired)
        top_pages = list(
            qs.values('path')
              .annotate(visits=Count('id'))
              .order_by('-visits')[:20]
        )

        # Top referrers (top 15)
        top_referrers = list(
            qs.exclude(referrer='')
              .values('referrer')
              .annotate(visits=Count('id'))
              .order_by('-visits')[:15]
        )

        return Response({
            'days':             days,
            'total_visits':     total_visits,
            'unique_visitors':  unique_visitors,
            'by_country':       by_country,
            'by_device':        by_device,
            'by_browser':       by_browser,
            'by_os':            by_os,
            'daily_trend':      daily_trend,
            'top_pages':        top_pages,
            'top_referrers':    top_referrers,
        })


# ── Content Flags / Reports ────────────────────────────────────────────────────

class CEContentFlagsView(APIView):
    """GET /api/editorial/ce/flags/?resolved=&type="""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.editorial.models import ContentFlag
        qs = ContentFlag.objects.select_related('chapter__story', 'flagged_by', 'resolved_by')
        resolved = request.query_params.get('resolved', '')
        flag_type= request.query_params.get('type', '')
        if resolved == '0':
            qs = qs.filter(resolved=False)
        elif resolved == '1':
            qs = qs.filter(resolved=True)
        if flag_type:
            qs = qs.filter(flag_type=flag_type)
        qs = qs.order_by('-created_at')[:100]

        data = [{
            'id':           f.id,
            'flag_type':    f.flag_type,
            'description':  f.description,
            'flagged_by':   f.flagged_by.username if f.flagged_by else '—',
            'chapter_id':   f.chapter_id,
            'chapter_num':  f.chapter.chapter_number if f.chapter else None,
            'story_title':  f.chapter.story.title if f.chapter and f.chapter.story else '—',
            'story_slug':   f.chapter.story.slug if f.chapter and f.chapter.story else None,
            'author':       f.chapter.story.author.username if f.chapter and f.chapter.story else '—',
            'resolved':     f.resolved,
            'resolution_note': f.resolution_note,
            'resolved_by':  f.resolved_by.username if f.resolved_by else None,
            'created_at':   f.created_at.isoformat(),
        } for f in qs]

        return Response({'count': len(data), 'results': data})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_resolve_flag(request, pk):
    """POST /api/editorial/ce/flags/<pk>/resolve/"""
    from apps.editorial.models import ContentFlag
    from django.utils import timezone
    flag = get_object_or_404(ContentFlag, pk=pk)
    flag.resolved      = True
    flag.resolution_note = request.data.get('note', '')
    flag.resolved_by   = request.user
    flag.save(update_fields=['resolved', 'resolution_note', 'resolved_by'])
    return Response({'detail': 'Flag resolved.'})


# ── Author Warnings ───────────────────────────────────────────────────────────

class CEAuthorWarningsView(APIView):
    """GET /api/editorial/ce/warnings/  — list all active warnings.
    POST — issue a new warning."""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.editorial.models import AuthorWarning
        from django.db.models import Q
        qs = AuthorWarning.objects.select_related('author', 'issued_by').filter(is_active=True)
        author_id = request.query_params.get('author_id')
        if author_id:
            qs = qs.filter(author_id=author_id)
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(author__username__icontains=search)
                | Q(author__author_code__iexact=search)
            )
        data = [{
            'id':          w.id,
            'author':      w.author.username,
            'author_id':   w.author.id,
            'author_code': w.author.author_code or '',
            'reason':      w.reason,
            'details':     w.details,
            'issued_by':   w.issued_by.username if w.issued_by else '—',
            'created_at':  w.created_at.isoformat(),
        } for w in qs]
        return Response({'count': len(data), 'results': data})

    def post(self, request):
        from apps.editorial.models import AuthorWarning
        from apps.users.models import User as _User
        from apps.notifications.services import create_notification
        from apps.notifications.models import Notification

        author_id = request.data.get('author_id')
        reason    = request.data.get('reason', 'other')
        details   = request.data.get('details', '')
        author    = get_object_or_404(_User, pk=author_id, role='author')

        warning = AuthorWarning.objects.create(
            author=author, issued_by=request.user, reason=reason, details=details
        )
        try:
            create_notification(
                user=author,
                notification_type=Notification.TYPE_SYSTEM,
                title='Official warning issued',
                message=f'You have received an official warning: {details[:120]}',
                data={'screen': 'my_books'},
            )
        except Exception:
            pass

        return Response({'detail': f'Warning issued to {author.username}.', 'id': warning.id}, status=201)


@api_view(['DELETE'])
@permission_classes([IsCE])
def ce_dismiss_warning(request, pk):
    """DELETE /api/editorial/ce/warnings/<pk>/"""
    from apps.editorial.models import AuthorWarning
    w = get_object_or_404(AuthorWarning, pk=pk)
    w.is_active = False
    w.save(update_fields=['is_active'])
    return Response({'detail': 'Warning dismissed.'})


# ── Author Reassignment ────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsCE])
def ce_reassign_author(request, author_id):
    """
    POST /api/editorial/ce/authors/<author_id>/reassign/

    Reassign an author to a different SE, or unassign them entirely.
    Body:
      { "se_id": 42, "reason": "optional note" }   → assign to SE #42
      { "se_id": null, "reason": "..." }            → unassign (remove SE)
    """
    _User = get_user_model()

    author = get_object_or_404(_User, pk=author_id, role='author')
    se_id  = request.data.get('se_id')
    reason = request.data.get('reason', '').strip()

    new_se = None
    if se_id is not None:
        new_se = get_object_or_404(_User, pk=se_id, role='se')

    link, _ = AuthorEditorLink.objects.get_or_create(author=author)
    old_se  = link.assigned_se

    if old_se == new_se:
        return Response(
            {'detail': 'Author is already assigned to this SE. No change made.'},
            status=400,
        )

    link.assigned_se  = new_se
    link.link_method  = AuthorEditorLink.LINK_MANUAL
    link.notes        = (
        f'Reassigned by CE {request.user.username} on {timezone.now().date()}'
        + (f'. Reason: {reason}' if reason else '')
        + f'. Previous SE: {old_se.username if old_se else "none"}.'
    )
    link.save(update_fields=['assigned_se', 'link_method', 'notes'])

    # Also update any open ContractApplication for this author's stories
    from apps.editorial.models import ContractApplication
    ContractApplication.objects.filter(
        author=author,
        status=ContractApplication.STATUS_PENDING,
    ).update(assigned_se=new_se)

    # Notify all three parties
    try:
        from apps.notifications.services import create_notification
        display = author.username
        if new_se:
            create_notification(
                new_se,
                'author_assigned',
                f'Author {display} has been assigned to you by CE {request.user.username}.',
            )
        if old_se:
            create_notification(
                old_se,
                'author_unassigned',
                f'Author {display} has been reassigned away from you by CE {request.user.username}.',
            )
        msg = (
            f'Your Senior Editor has been changed to {new_se.username}.'
            if new_se else
            'You have been unassigned from your Senior Editor. The CE will assign a new one shortly.'
        )
        create_notification(author, 'se_reassigned', msg)
    except Exception:
        pass

    return Response({
        'ok':     True,
        'author': author.username,
        'old_se': old_se.username if old_se else None,
        'new_se': new_se.username if new_se else None,
    })


# ── Author Messages / Complaints ──────────────────────────────────────────────

class CEAuthorMessagesView(APIView):
    """GET /api/editorial/ce/messages/  POST (author sends a message)."""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.editorial.models import AuthorMessage
        qs = AuthorMessage.objects.select_related('author', 'replied_by').order_by('-created_at')[:200]
        unread = request.query_params.get('unread', '')
        if unread == '1':
            qs = qs.filter(is_read=False)
        data = [{
            'id':        m.id,
            'author':    m.author.username,
            'author_id': m.author.id,
            'subject':   m.subject,
            'body':      m.body,
            'msg_type':  m.msg_type,
            'is_read':   m.is_read,
            'ce_reply':  m.ce_reply,
            'replied_by': m.replied_by.username if m.replied_by else None,
            'created_at': m.created_at.isoformat(),
        } for m in qs]
        return Response({'count': len(data), 'results': data})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_reply_message(request, pk):
    """POST /api/editorial/ce/messages/<pk>/reply/"""
    from apps.editorial.models import AuthorMessage
    from apps.notifications.services import create_notification
    from apps.notifications.models import Notification
    from django.utils import timezone

    msg = get_object_or_404(AuthorMessage, pk=pk)
    reply = request.data.get('reply', '').strip()
    if not reply:
        return Response({'detail': 'Reply text required.'}, status=400)

    msg.ce_reply   = reply
    msg.replied_by = request.user
    msg.replied_at = timezone.now()
    msg.is_read    = True
    msg.save(update_fields=['ce_reply', 'replied_by', 'replied_at', 'is_read'])

    try:
        create_notification(
            user=msg.author,
            notification_type=Notification.TYPE_SYSTEM,
            title='Response to your message',
            message=f'The CE has replied to your message: "{msg.subject}"',
        )
    except Exception:
        pass

    return Response({'detail': 'Reply sent.'})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_mark_message_read(request, pk):
    from apps.editorial.models import AuthorMessage
    msg = get_object_or_404(AuthorMessage, pk=pk)
    msg.is_read = True
    msg.save(update_fields=['is_read'])
    return Response({'detail': 'Marked as read.'})


# ── Author-facing announcements ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def author_announcements(request):
    """GET /api/editorial/announcements/
    Returns sent announcements visible to the requesting author."""
    from apps.editorial.models import Announcement
    qs = Announcement.objects.filter(
        is_sent=True,
        target__in=['all', 'authors'],
    ).order_by('-created_at')[:50]
    data = [{
        'id':         a.id,
        'title':      a.title,
        'body':       a.body,
        'sent_by':    a.sent_by.get_full_name() or a.sent_by.username if a.sent_by else 'NoveluX',
        'created_at': a.created_at.isoformat(),
    } for a in qs]
    return Response({'count': len(data), 'results': data})


# ── System Notice (admin broadcast) ──────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def system_notice(request):
    """GET /api/editorial/system-notice/
    Returns the currently active admin system notice (if any)."""
    from apps.editorial.models import SystemNotice
    notice = SystemNotice.objects.filter(is_active=True).order_by('-created_at').first()
    if not notice:
        return Response(None)
    return Response({
        'id':           notice.id,
        'message':      notice.message,
        'notice_type':  notice.notice_type,
        'cta_label':    notice.cta_label,
        'cta_url':      notice.cta_url,
    })


# ── Announcements ─────────────────────────────────────────────────────────────

class CEAnnouncementsView(APIView):
    """GET /api/editorial/ce/announcements/
    POST — create and optionally send an announcement."""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.editorial.models import Announcement
        qs = Announcement.objects.select_related('sent_by').order_by('-created_at')[:100]
        data = [{
            'id':         a.id,
            'title':      a.title,
            'body':       a.body,
            'target':     a.target,
            'is_sent':    a.is_sent,
            'sent_by':    a.sent_by.username if a.sent_by else '—',
            'created_at': a.created_at.isoformat(),
            'sent_at':    a.sent_at.isoformat() if a.sent_at else None,
        } for a in qs]
        return Response({'count': len(data), 'results': data})

    def post(self, request):
        from apps.editorial.models import Announcement
        from apps.users.models import User as _User
        from apps.notifications.services import notify_user
        from apps.notifications.models import Notification
        from apps.notifications.fcm import send_to_tokens
        from apps.users.models import FCMDevice
        from django.utils import timezone

        title   = request.data.get('title', '').strip()
        body    = request.data.get('body', '').strip()
        target  = request.data.get('target', 'all')
        send_now= request.data.get('send_now', True)

        if not title or not body:
            return Response({'detail': 'title and body required.'}, status=400)

        ann = Announcement.objects.create(
            title=title, body=body, target=target, sent_by=request.user
        )

        pushed = 0
        if send_now:
            # Build recipient queryset
            if target == 'authors':
                users = _User.objects.filter(role='author', is_active=True)
            elif target == 'ses':
                users = _User.objects.filter(role='se', is_active=True)
            else:
                users = _User.objects.filter(is_active=True)

            # Bulk-create in-app notifications
            Notification.objects.bulk_create([
                Notification(
                    recipient=u,
                    notification_type=Notification.TYPE_SYSTEM,
                    title=f'📢 {title}',
                    message=body[:255],
                    data={'screen': 'announcements'},
                )
                for u in users
            ], batch_size=500)

            # FCM push
            tokens = list(
                FCMDevice.objects.filter(user__in=users, is_active=True)
                .values_list('token', flat=True)
            )
            if tokens:
                from apps.notifications.fcm import send_to_tokens as _push
                _push(tokens, title=f'📢 {title}', body=body[:200])
                pushed = len(tokens)

            ann.is_sent = True
            ann.sent_at = timezone.now()
            ann.save(update_fields=['is_sent', 'sent_at'])

        return Response({
            'detail':  f'Announcement {"sent" if send_now else "saved"}.',
            'id':      ann.id,
            'pushed':  pushed,
        }, status=201)


# ── SE Promotion Requests ─────────────────────────────────────────────────────

class CESEPromotionRequestsView(APIView):
    """GET /api/editorial/ce/promotion-requests/  ?status=pending|approved|rejected  &tab=  &section="""
    permission_classes = [IsCE]

    def get(self, request):
        from apps.editorial.models import SEPromotionRequest
        qs = SEPromotionRequest.objects.select_related('se', 'story', 'reviewed_by').order_by('-created_at')
        if request.query_params.get('status'):
            qs = qs.filter(status=request.query_params['status'])
        if request.query_params.get('tab'):
            qs = qs.filter(tab=request.query_params['tab'])
        if request.query_params.get('section'):
            qs = qs.filter(section=request.query_params['section'])
        data = [{
            'id':          r.id,
            'se':          r.se.username,
            'se_id':       r.se.id,
            'story_title': r.story.title,
            'story_slug':  r.story.slug,
            'tab':         r.tab,
            'section':     r.section,
            'message':     r.message,
            'status':      r.status,
            'ce_note':     r.ce_note,
            'created_at':  r.created_at.isoformat(),
            'reviewed_by': r.reviewed_by.username if r.reviewed_by else None,
        } for r in qs]
        return Response({'count': len(data), 'results': data})


@api_view(['POST'])
@permission_classes([IsCE])
def ce_review_promotion(request, pk):
    """POST /api/editorial/ce/promotion-requests/<pk>/review/
    Body: { "action": "approved"|"rejected", "note": "...", "order": 0 }
    On approval, creates or reactivates an ExploreTabPin for the story.
    """
    from apps.editorial.models import SEPromotionRequest, ExploreTabPin
    from apps.notifications.services import create_notification
    from apps.notifications.models import Notification
    from django.utils import timezone

    req    = get_object_or_404(SEPromotionRequest, pk=pk)
    action = request.data.get('action', 'approved')
    note   = request.data.get('note', '')
    order  = int(request.data.get('order', 0))

    if action not in ('approved', 'rejected'):
        return Response({'detail': 'action must be approved or rejected.'}, status=400)

    req.status      = action
    req.ce_note     = note
    req.reviewed_by = request.user
    req.reviewed_at = timezone.now()
    req.save(update_fields=['status', 'ce_note', 'reviewed_by', 'reviewed_at'])

    if action == 'approved':
        pin, _ = ExploreTabPin.objects.update_or_create(
            tab=req.tab,
            section=req.section,
            story=req.story,
            defaults={
                'pinned_by':      request.user,
                'source_request': req,
                'is_active':      True,
                'order':          order,
            },
        )

    try:
        create_notification(
            user=req.se,
            notification_type=Notification.TYPE_SYSTEM,
            title=f'Promotion request {action}',
            message=f'Your promotion request for "{req.story.title}" was {action}.{" Note: " + note if note else ""}',
        )
    except Exception:
        pass

    return Response({'ok': True, 'action': action})


# ── CE Explore Tab Pins (direct management) ───────────────────────────────────

class CETabPinsView(APIView):
    """
    GET  /api/editorial/ce/tab-pins/          ?tab=  &section=  &active=true
    POST /api/editorial/ce/tab-pins/
         Body: { story_slug, tab, section, order=0 }
         CE directly pins a story without an SE request.
    """
    permission_classes = [IsCE]

    def get(self, request):
        from apps.editorial.models import ExploreTabPin
        qs = ExploreTabPin.objects.select_related('story', 'pinned_by', 'source_request__se').order_by('tab', 'section', 'order')
        if request.query_params.get('tab'):
            qs = qs.filter(tab=request.query_params['tab'])
        if request.query_params.get('section'):
            qs = qs.filter(section=request.query_params['section'])
        active = request.query_params.get('active', '')
        if active.lower() == 'true':
            qs = qs.filter(is_active=True)
        elif active.lower() == 'false':
            qs = qs.filter(is_active=False)

        data = [{
            'id':            p.id,
            'tab':           p.tab,
            'section':       p.section,
            'story_title':   p.story.title,
            'story_slug':    p.story.slug,
            'order':         p.order,
            'is_active':     p.is_active,
            'pinned_by':     p.pinned_by.username,
            'pinned_at':     p.pinned_at.isoformat(),
            'from_request':  p.source_request_id,
            'requested_by':  p.source_request.se.username if p.source_request else None,
        } for p in qs]
        return Response({'count': len(data), 'results': data})

    def post(self, request):
        from apps.editorial.models import ExploreTabPin
        from apps.stories.models import Story

        VALID_TABS = {'werewolf', 'billionaire', 'short-fics', 'ranking', 'for-her', 'for-him', 'suspense'}

        slug    = request.data.get('story_slug', '').strip()
        tab     = request.data.get('tab', '').strip()
        section = request.data.get('section', '').strip()
        order   = int(request.data.get('order', 0))

        if not slug:
            return Response({'detail': 'story_slug is required.'}, status=400)
        if not tab or tab not in VALID_TABS:
            return Response({'detail': f'tab must be one of: {", ".join(sorted(VALID_TABS))}'}, status=400)
        if not section:
            return Response({'detail': 'section is required.'}, status=400)

        story = get_object_or_404(Story, slug=slug)

        pin, created = ExploreTabPin.objects.update_or_create(
            tab=tab, section=section, story=story,
            defaults={'pinned_by': request.user, 'is_active': True, 'order': order, 'source_request': None},
        )
        return Response({
            'ok':          True,
            'id':          pin.id,
            'story_title': story.title,
            'tab':         pin.tab,
            'section':     pin.section,
            'created':     created,
        }, status=201 if created else 200)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsCE])
def ce_tab_pin_detail(request, pk):
    """
    PATCH  /api/editorial/ce/tab-pins/<pk>/  — update order or toggle is_active
           Body: { "is_active": true|false, "order": 0 }
    DELETE /api/editorial/ce/tab-pins/<pk>/  — permanently remove the pin
    """
    from apps.editorial.models import ExploreTabPin

    pin = get_object_or_404(ExploreTabPin, pk=pk)

    if request.method == 'DELETE':
        pin.delete()
        return Response({'ok': True, 'deleted': pk})

    # PATCH
    if 'is_active' in request.data:
        pin.is_active = bool(request.data['is_active'])
    if 'order' in request.data:
        pin.order = int(request.data['order'])
    pin.save(update_fields=['is_active', 'order'])
    return Response({'ok': True, 'id': pin.id, 'is_active': pin.is_active, 'order': pin.order})


# ── CE Story Push Notification ────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsCE])
def ce_story_push(request, slug):
    """POST /api/editorial/ce-story-queue/<slug>/push/
    Body: {
      "title":   "New chapter out!",
      "body":    "Check out the latest from ...",
      "target":  "all" | "bookmarked" | "author_followers"
    }
    Sends a push notification about a specific story to the chosen audience.
    """
    from apps.stories.models import Story, Bookmark
    from apps.users.models import FCMDevice
    from apps.notifications.fcm import send_to_tokens
    from apps.notifications.models import Notification
    import django.db.models as _m

    title  = request.data.get('title', '').strip()
    body   = request.data.get('body', '').strip()
    target = request.data.get('target', 'all')

    if not title or not body:
        return Response({'detail': 'title and body are required.'}, status=400)
    if target not in ('all', 'bookmarked', 'author_followers'):
        return Response({'detail': 'target must be all, bookmarked, or author_followers.'}, status=400)

    story = get_object_or_404(Story, slug=slug)
    image_url = ''
    if story.cover_image:
        try:
            image_url = request.build_absolute_uri(story.cover_image.url)
        except Exception:
            pass

    # Resolve the target audience
    User = get_user_model()
    if target == 'bookmarked':
        user_ids = Bookmark.objects.filter(story=story).values_list('user_id', flat=True)
        users = User.objects.filter(id__in=user_ids, is_active=True)
    elif target == 'author_followers':
        from apps.users.models import Follow
        user_ids = Follow.objects.filter(following=story.author).values_list('follower_id', flat=True)
        users = User.objects.filter(id__in=user_ids, is_active=True)
    else:
        users = User.objects.filter(is_active=True)

    # In-app notifications
    Notification.objects.bulk_create([
        Notification(
            recipient=u,
            notification_type=Notification.TYPE_NEW_CHAPTER,
            title=title,
            message=body[:255],
            data={'screen': 'story', 'slug': story.slug},
        )
        for u in users
    ], batch_size=500)

    # FCM push
    tokens = list(
        FCMDevice.objects.filter(user__in=users, is_active=True)
        .values_list('token', flat=True)
    )
    pushed = 0
    if tokens:
        result = send_to_tokens(
            tokens,
            title=title,
            body=body[:200],
            data={'screen': 'story', 'slug': story.slug},
            image_url=image_url,
        )
        pushed = result.get('success', 0)

    return Response({
        'detail': 'Push notification sent.',
        'target': target,
        'recipients': len(tokens),
        'pushed': pushed,
    })


# ══════════════════════════════════════════════════════════════════════════════
# SE / CE  Promotion Slot Management
# ══════════════════════════════════════════════════════════════════════════════

def _promotion_data(promo):
    return {
        'id':             promo.id,
        'story_id':       promo.story_id,
        'story_title':    promo.story.title,
        'story_slug':     promo.story.slug,
        'category':       promo.category,
        'category_label': promo.get_category_display(),
        'status':         promo.status,
        'starts_at':      promo.starts_at.isoformat(),
        'expires_at':     promo.expires_at.isoformat(),
        'queue_position': promo.queue_position,
        'se':             promo.se.username,
    }


class SEPromotionListCreateView(APIView):
    """
    GET  /api/editorial/promotions/          — list my promotions + slot usage
    POST /api/editorial/promotions/          — add a story to a promotion slot
         body: { story_id, category, starts_at, expires_at }
    """
    permission_classes = [IsSE]

    def get(self, request):
        from .models import StoryPromotion, PromotionSlotConfig, PROMOTION_CATEGORY_CHOICES
        from django.utils.timezone import now

        promos = (
            StoryPromotion.objects
            .filter(se=request.user)
            .exclude(status=StoryPromotion.STATUS_EXPIRED)
            .select_related('story')
            .order_by('category', 'queue_position', 'created_at')
        )

        # Slot usage summary per category
        slot_usage = []
        for cat_slug, cat_label in PROMOTION_CATEGORY_CHOICES:
            active = StoryPromotion.active_count(request.user, cat_slug)
            limit  = StoryPromotion.get_slot_limit(request.user, cat_slug)
            slot_usage.append({
                'category':       cat_slug,
                'category_label': cat_label,
                'active':         active,
                'limit':          limit,
                'queued':         StoryPromotion.objects.filter(
                    se=request.user, category=cat_slug, status=StoryPromotion.STATUS_QUEUED
                ).count(),
            })

        return Response({
            'slot_usage':  slot_usage,
            'promotions':  [_promotion_data(p) for p in promos],
        })

    def post(self, request):
        from .models import StoryPromotion
        from apps.stories.models import Story
        from django.utils.timezone import now
        from django.utils.dateparse import parse_datetime

        story_id   = request.data.get('story_id')
        category   = request.data.get('category', '')
        starts_raw = request.data.get('starts_at')
        expires_raw= request.data.get('expires_at')

        if not all([story_id, category, starts_raw, expires_raw]):
            return Response({'detail': 'story_id, category, starts_at, expires_at are required.'}, status=400)

        valid_cats = [c[0] for c in StoryPromotion._meta.get_field('category').choices]
        if category not in valid_cats:
            return Response({'detail': f'Invalid category. Choose from: {valid_cats}'}, status=400)

        story = get_object_or_404(Story, pk=story_id)
        starts_at  = parse_datetime(starts_raw)
        expires_at = parse_datetime(expires_raw)

        if not starts_at or not expires_at or expires_at <= starts_at:
            return Response({'detail': 'Invalid date range.'}, status=400)

        # Determine status: active if slot available AND starts now/past, else queued
        slot_free = StoryPromotion.can_add_active(request.user, category)
        is_future = starts_at > now()
        status    = StoryPromotion.STATUS_ACTIVE if (slot_free and not is_future) else StoryPromotion.STATUS_QUEUED

        # Queue position = count of existing queued + 1
        queue_pos = 0
        if status == StoryPromotion.STATUS_QUEUED:
            queue_pos = StoryPromotion.objects.filter(
                se=request.user, category=category, status=StoryPromotion.STATUS_QUEUED
            ).count() + 1

        promo = StoryPromotion.objects.create(
            se=request.user, story=story, category=category,
            status=status, starts_at=starts_at, expires_at=expires_at,
            queue_position=queue_pos,
        )
        return Response(_promotion_data(promo), status=201)


@api_view(['DELETE'])
@permission_classes([IsSE])
def se_remove_promotion(request, pk):
    """DELETE /api/editorial/promotions/<pk>/ — remove own promotion."""
    from .models import StoryPromotion
    promo = get_object_or_404(StoryPromotion, pk=pk, se=request.user)
    promo.delete()
    return Response({'detail': 'Promotion removed.'}, status=204)


# ── CE: view all + manage slot configs ───────────────────────────────────────

class CEPromotionListView(APIView):
    """GET /api/editorial/ce/promotions/ — all active/queued promotions across all SEs."""
    permission_classes = [IsCE]

    def get(self, request):
        from .models import StoryPromotion
        promos = (
            StoryPromotion.objects
            .exclude(status=StoryPromotion.STATUS_EXPIRED)
            .select_related('story', 'se')
            .order_by('category', 'se__username', 'queue_position')
        )
        return Response({'count': promos.count(), 'promotions': [_promotion_data(p) for p in promos]})


@api_view(['DELETE'])
@permission_classes([IsCE])
def ce_remove_promotion(request, pk):
    """DELETE /api/editorial/ce/promotions/<pk>/ — remove any SE promotion."""
    from .models import StoryPromotion
    promo = get_object_or_404(StoryPromotion, pk=pk)
    promo.delete()
    return Response({'detail': 'Promotion removed.'}, status=204)


class CESlotConfigView(APIView):
    """
    GET  /api/editorial/ce/slot-configs/   — view all slot configs
    POST /api/editorial/ce/slot-configs/   — set/update a slot limit
         body: { category, slot_limit, se_id (optional — omit for global default) }
    """
    permission_classes = [IsCE]

    def get(self, request):
        from .models import PromotionSlotConfig, PROMOTION_CATEGORY_CHOICES
        configs = list(
            PromotionSlotConfig.objects.select_related('se', 'set_by')
            .values('id', 'category', 'slot_limit', 'se__id', 'se__username',
                    'set_by__username', 'updated_at')
        )
        # Fill in defaults for categories with no config
        configured = {(c['category'], c['se__id']) for c in configs}
        defaults = []
        for cat_slug, cat_label in PROMOTION_CATEGORY_CHOICES:
            if (cat_slug, None) not in configured:
                defaults.append({'category': cat_slug, 'category_label': cat_label,
                                  'slot_limit': 5, 'se': None, 'is_default': True})
        return Response({'configs': configs, 'unconfigured_defaults': defaults})

    def post(self, request):
        from .models import PromotionSlotConfig
        from apps.users.models import User as _User

        category   = request.data.get('category', '')
        slot_limit = request.data.get('slot_limit')
        se_id      = request.data.get('se_id')   # null = global default

        if not category or slot_limit is None:
            return Response({'detail': 'category and slot_limit are required.'}, status=400)

        try:
            slot_limit = int(slot_limit)
            if slot_limit < 1:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'detail': 'slot_limit must be a positive integer.'}, status=400)

        se = None
        if se_id:
            se = get_object_or_404(_User, pk=se_id, role='se')

        config, _ = PromotionSlotConfig.objects.update_or_create(
            category=category, se=se,
            defaults={'slot_limit': slot_limit, 'set_by': request.user},
        )
        return Response({
            'id':         config.id,
            'category':   config.category,
            'slot_limit': config.slot_limit,
            'se':         se.username if se else None,
            'set_by':     request.user.username,
        })



# ── Chapter edit requests ──────────────────────────────────────────────────

class SEChapterEditQueueView(generics.ListAPIView):
    """GET /api/editorial/chapter-edits/  — SE sees pending chapter edits for their authors."""
    permission_classes = [IsSEOrAbove]

    def list(self, request, *args, **kwargs):
        from apps.chapters.models import ChapterEditRequest
        from apps.editorial.models import AuthorEditorLink

        author_ids = AuthorEditorLink.objects.filter(
            assigned_se=request.user
        ).values_list('author_id', flat=True)

        status_filter = request.query_params.get('status', ChapterEditRequest.STATUS_PENDING)
        qs = ChapterEditRequest.objects.filter(
            author_id__in=author_ids, status=status_filter
        ).select_related('chapter__story', 'author').order_by('-submitted_at')

        data = []
        for req in qs:
            data.append({
                'id':              req.pk,
                'author':          req.author.username,
                'story_title':     req.chapter.story.title,
                'story_slug':      req.chapter.story.slug,
                'chapter_number':  req.chapter.chapter_number,
                'chapter_title':   req.chapter.title,
                'pending_title':   req.pending_title,
                'pending_content': req.pending_content,
                'status':          req.status,
                'se_note':         req.se_note,
                'submitted_at':    req.submitted_at,
                'reviewed_at':     req.reviewed_at,
            })
        return Response(data)


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_review_chapter_edit(request, pk):
    """
    POST /api/editorial/chapter-edits/<id>/review/
    SE approves or rejects a chapter edit request.
    Body: { "action": "approve"|"reject", "note": "..." }
    """
    from apps.chapters.models import ChapterEditRequest
    from apps.editorial.models import AuthorEditorLink

    edit_req = get_object_or_404(ChapterEditRequest, pk=pk,
                                  status=ChapterEditRequest.STATUS_PENDING)

    if not AuthorEditorLink.objects.filter(
        assigned_se=request.user, author=edit_req.author
    ).exists():
        return Response({'detail': 'This author is not assigned to you.'}, status=403)

    action = request.data.get('action', '').strip()
    if action not in ('approve', 'reject'):
        return Response({'detail': "action must be 'approve' or 'reject'"}, status=400)

    edit_req.status      = ChapterEditRequest.STATUS_APPROVED if action == 'approve' else ChapterEditRequest.STATUS_REJECTED
    edit_req.se_note     = request.data.get('note', '').strip()
    edit_req.reviewed_by = request.user
    edit_req.reviewed_at = timezone.now()
    edit_req.save(update_fields=['status', 'se_note', 'reviewed_by', 'reviewed_at'])

    chapter = edit_req.chapter
    if action == 'approve':
        chapter.title   = edit_req.pending_title or chapter.title
        chapter.content = edit_req.pending_content
        chapter.save(update_fields=['title', 'content', 'word_count', 'updated_at'])
    elif edit_req.original_content:
        # Rejected — restore the chapter to the version it had before the
        # author's edit (snapshotted when the review cycle started).
        chapter.title   = edit_req.original_title or chapter.title
        chapter.content = edit_req.original_content
        chapter.save(update_fields=['title', 'content', 'word_count', 'updated_at'])

    # Review is done either way — take the chapter out of the SE incoming
    # queue by restoring its 'published' status (it stayed live throughout).
    if chapter.is_published:
        from apps.chapters.models import Chapter as _Chapter
        _Chapter.objects.filter(pk=chapter.pk).update(
            status=_Chapter.STATUS_PUBLISHED,
        )

    try:
        from apps.notifications.services import create_notification
        ch = edit_req.chapter
        if action == 'approve':
            msg = f'Your edit for "{ch.story.title}" Ch.{ch.chapter_number} has been approved and is now live.'
        else:
            note = edit_req.se_note
            msg  = (f'Your edit for "{ch.story.title}" Ch.{ch.chapter_number} was not approved '
                    f'and the chapter was restored to its previous version. {note}')
        create_notification(edit_req.author, 'chapter_edit_update', msg)
    except Exception:
        pass

    return Response({'ok': True, 'status': edit_req.status})


# ── Story cover change requests ────────────────────────────────────────────

class SECoverRequestQueueView(generics.ListAPIView):
    """GET /api/editorial/cover-requests/  — SE sees pending cover changes for their authors."""
    permission_classes = [IsSEOrAbove]

    def list(self, request, *args, **kwargs):
        from apps.stories.models import StoryCoverRequest
        from apps.editorial.models import AuthorEditorLink

        author_ids = AuthorEditorLink.objects.filter(
            assigned_se=request.user
        ).values_list('author_id', flat=True)

        status_filter = request.query_params.get('status', StoryCoverRequest.STATUS_PENDING)
        qs = StoryCoverRequest.objects.filter(
            author_id__in=author_ids, status=status_filter
        ).select_related('story', 'author').order_by('-submitted_at')

        data = []
        for req in qs:
            data.append({
                'id':            req.pk,
                'author':        req.author.username,
                'story_title':   req.story.title,
                'story_slug':    req.story.slug,
                'current_cover': request.build_absolute_uri(req.story.cover_image.url)
                                 if req.story.cover_image else None,
                'pending_cover': request.build_absolute_uri(req.pending_cover.url),
                'status':        req.status,
                'se_note':       req.se_note,
                'submitted_at':  req.submitted_at,
                'reviewed_at':   req.reviewed_at,
            })
        return Response(data)


@api_view(['POST'])
@permission_classes([IsSEOrAbove])
def se_review_cover_request(request, pk):
    """
    POST /api/editorial/cover-requests/<id>/review/
    SE approves or rejects a story cover change.
    Body: { "action": "approve"|"reject", "note": "..." }
    """
    from apps.stories.models import StoryCoverRequest
    from apps.editorial.models import AuthorEditorLink

    cover_req = get_object_or_404(StoryCoverRequest, pk=pk,
                                   status=StoryCoverRequest.STATUS_PENDING)

    if not AuthorEditorLink.objects.filter(
        assigned_se=request.user, author=cover_req.author
    ).exists():
        return Response({'detail': 'This author is not assigned to you.'}, status=403)

    action = request.data.get('action', '').strip()
    if action not in ('approve', 'reject'):
        return Response({'detail': "action must be 'approve' or 'reject'"}, status=400)

    cover_req.status      = StoryCoverRequest.STATUS_APPROVED if action == 'approve' else StoryCoverRequest.STATUS_REJECTED
    cover_req.se_note     = request.data.get('note', '').strip()
    cover_req.reviewed_by = request.user
    cover_req.reviewed_at = timezone.now()
    cover_req.save(update_fields=['status', 'se_note', 'reviewed_by', 'reviewed_at'])

    if action == 'approve':
        story = cover_req.story
        story.cover_image = cover_req.pending_cover
        story.save(update_fields=['cover_image'])

    try:
        from apps.notifications.services import create_notification
        if action == 'approve':
            msg = f'Your new cover for "{cover_req.story.title}" has been approved and is now live.'
        else:
            note = cover_req.se_note
            msg  = f'Your cover change for "{cover_req.story.title}" was not approved. {note}'
        create_notification(cover_req.author, 'cover_update', msg)
    except Exception:
        pass

    return Response({'ok': True, 'status': cover_req.status})
