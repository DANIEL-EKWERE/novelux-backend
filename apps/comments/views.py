from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Comment, CommentLike
from .serializers import CommentSerializer, CreateCommentSerializer
from apps.stories.models import Story
from apps.chapters.models import Chapter
from apps.users.permissions import IsOwnerOrReadOnly


class ChapterCommentListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return CreateCommentSerializer if self.request.method == 'POST' else CommentSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.request.method == 'POST' else [permissions.AllowAny()]

    def get_queryset(self):
        chapter = get_object_or_404(
            Chapter,
            story__slug=self.kwargs['story_slug'],
            chapter_number=self.kwargs['chapter_number']
        )
        return Comment.objects.filter(chapter=chapter, parent=None).select_related('user')

    def perform_create(self, serializer):
        story   = get_object_or_404(Story, slug=self.kwargs['story_slug'])
        chapter = get_object_or_404(Chapter, story=story, chapter_number=self.kwargs['chapter_number'])
        comment = serializer.save(
            user=self.request.user,
            story=story,
            chapter=chapter,
            is_author_reply=(self.request.user == story.author),
        )
        Story.objects.filter(pk=story.pk).update(
            total_comments=__import__('django.db.models', fromlist=['F']).F('total_comments') + 1
        )
        return comment


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = CommentSerializer
    permission_classes = [IsOwnerOrReadOnly]
    queryset           = Comment.objects.all()


class LikeCommentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        _, created = CommentLike.objects.get_or_create(user=request.user, comment=comment)
        if created:
            Comment.objects.filter(pk=pk).update(likes_count=__import__('django.db.models', fromlist=['F']).F('likes_count') + 1)
        return Response({'liked': True}, status=201 if created else 200)

    def delete(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        deleted, _ = CommentLike.objects.filter(user=request.user, comment=comment).delete()
        if deleted:
            Comment.objects.filter(pk=pk).update(likes_count=__import__('django.db.models', fromlist=['F']).F('likes_count') - 1)
        return Response({'liked': False}, status=204)


class PinCommentView(APIView):
    """Only story author can pin a comment."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        if comment.story.author != request.user:
            return Response({'detail': 'Only the story author can pin comments.'}, status=403)
        Comment.objects.filter(story=comment.story, chapter=comment.chapter, is_pinned=True).update(is_pinned=False)
        comment.is_pinned = True
        comment.save(update_fields=['is_pinned'])
        return Response({'pinned': True})


class FlagCommentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        comment.is_flagged = True
        comment.save(update_fields=['is_flagged'])
        return Response({'flagged': True})
