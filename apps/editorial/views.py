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
    """GET /api/editorial/story-queue/ — stories awaiting SE review."""
    permission_classes = [IsSE]

    def get(self, request, *args, **kwargs):
        from apps.stories.models import Story
        from apps.editorial.models import ContractApplication

        stories = Story.objects.filter(
            contract_status='under_review',
            author__editor_link__assigned_se=request.user,
        ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

        data = []
        for s in stories:
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
            except ContractApplication.DoesNotExist:
                app_status = 'pending'
                app_id = None
                se_note = ''

            data.append({
                'id':              s.id,
                'slug':            s.slug,
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
                    'username':     s.author.username,
                    'display_name': s.author.get_full_name() or s.author.username,
                    'email':        s.author.email,
                },
                'application': {
                    'id':     app_id,
                    'status': app_status,
                    'note':   se_note,
                },
                'chapters': chapters,
                'submitted_at': s.updated_at,
            })

        return Response({'count': len(data), 'results': data})


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

        return Response({
            'id':              story.id,
            'slug':            story.slug,
            'title':           story.title,
            'description':     story.description,
            'cover_image':     story.cover_image.url if story.cover_image else '',
            'status':          story.status,
            'contract_status': story.contract_status,
            'word_count':      story.word_count,
            'total_chapters':  story.chapters.count(),
            'author': {
                'id':           story.author.id,
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
        contract_status='under_review',
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
        contract_status='under_review',
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

        stories = Story.objects.filter(
            contract_status='contract_sent',
        ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

        data = []
        for s in stories:
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
            'id':              story.id,
            'slug':            story.slug,
            'title':           story.title,
            'synopsis':        story.synopsis,
            'description':     story.description,
            'story_outline':   story.story_outline,
            'cover_image':     story.cover_image.url if story.cover_image else '',
            'status':          story.status,
            'contract_status': story.contract_status,
            'word_count':      story.word_count,
            'total_chapters':  story.chapters.count(),
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
            sign_url       = f'https://novelux.onrender.com/my-books/{_slug_cap}/contract/'
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
        ).update(contract_status='signed', contract_eligible=False, status='draft')
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

    # Mark story as signed. Do NOT set status='ongoing' yet — the story goes live
    # only once the author writes enough post-contract chapters to hit the
    # platform word count threshold (checked in Chapter._check_editorial_trigger).
    from apps.stories.models import Story
    story_slug = request.data.get('slug', '').strip()
    # Force status back to 'draft' so the story is NOT visible to readers
    # until the post-contract word-count threshold is hit in _check_editorial_trigger.
    # Snapshot current word_count so _check_editorial_trigger can measure only
    # words written AFTER signing (post-contract words = total - words_at_signing).
    from django.db.models import F
    updated = Story.objects.filter(
        author=user,
        contract_status='awaiting_signature',
    ).update(contract_status='signed', contract_eligible=False, status='draft', words_at_signing=F('word_count'))
    logger.info('accept_contract: signed %d stories for user %s', updated, user.username)

    # If the specific story wasn't matched, verify it is in awaiting_signature before force-updating
    if updated == 0 and story_slug:
        force_qs = Story.objects.filter(author=user, slug=story_slug, contract_status='awaiting_signature')
        if force_qs.exists():
            from django.db.models import F
            force_qs.update(contract_status='signed', contract_eligible=False, status='draft', words_at_signing=F('word_count'))
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

    # Chapters stay held — they publish automatically once the post-contract
    # word count threshold is hit (see Chapter._check_editorial_trigger Case A).
    published_count = 0
    logger.info('accept_contract: contract signed for user %s — story will go live after word threshold', user.username)

    # In-app notification
    try:
        from apps.notifications.services import on_contract_signed
        from apps.stories.models import Story as _S
        signed_story = _S.objects.filter(author=user, contract_status='signed').first()
        if signed_story:
            on_contract_signed(user, signed_story, published_count)
    except Exception:
        pass

    return Response({
        'status': 'contract_accepted',
        'published_chapters': published_count,
    })


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

    kyc.status      = AuthorKYC.STATUS_APPROVED if action == 'approve' else AuthorKYC.STATUS_REJECTED
    kyc.admin_notes = note
    kyc.reviewed_at = timezone.now()
    kyc.save(update_fields=['status', 'admin_notes', 'reviewed_at'])

    try:
        from apps.notifications.services import create_notification
        msg = (
            'Your identity verification has been approved.'
            if action == 'approve'
            else f'Your identity verification was rejected. {note}'
        )
        create_notification(kyc.user, 'kyc_update', msg)
    except Exception:
        pass

    return Response({'ok': True, 'status': kyc.status})
