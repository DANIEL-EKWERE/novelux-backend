from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import BranchPoint, BranchChoice, BranchVote
from .serializers import BranchPointSerializer, CreateBranchPointSerializer, CastVoteSerializer
from apps.chapters.models import Chapter
from apps.stories.models import Story


class ChapterBranchPointsView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return CreateBranchPointSerializer if self.request.method == 'POST' else BranchPointSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.request.method == 'POST' else [permissions.AllowAny()]

    def get_queryset(self):
        chapter = get_object_or_404(
            Chapter,
            story__slug=self.kwargs['story_slug'],
            chapter_number=self.kwargs['chapter_number']
        )
        return BranchPoint.objects.filter(chapter=chapter).prefetch_related('choices')

    def perform_create(self, serializer):
        story = get_object_or_404(Story, slug=self.kwargs['story_slug'])
        if story.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the author can create branch points.')
        serializer.save()


class CastVoteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, branch_point_id):
        branch_point = get_object_or_404(BranchPoint, pk=branch_point_id)

        if not branch_point.voting_open:
            return Response({'detail': 'Voting is closed.'}, status=400)

        if branch_point.voting_ends and timezone.now() > branch_point.voting_ends:
            branch_point.voting_open = False
            branch_point.save(update_fields=['voting_open'])
            return Response({'detail': 'Voting period has ended.'}, status=400)

        if BranchVote.objects.filter(user=request.user, branch_point=branch_point).exists():
            return Response({'detail': 'You have already voted.'}, status=400)

        serializer = CastVoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        choice = get_object_or_404(BranchChoice, pk=serializer.validated_data['choice_id'],
                                   branch_point=branch_point)
        BranchVote.objects.create(
            user=request.user, branch_point=branch_point, choice=choice
        )
        BranchChoice.objects.filter(pk=choice.pk).update(
            votes_count=__import__('django.db.models', fromlist=['F']).F('votes_count') + 1
        )

        return Response({
            'detail':    'Vote cast!',
            'choice_id': choice.id,
            'label':     choice.label,
        }, status=201)


class BranchPointResultsView(APIView):
    """Close voting and declare winner."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, branch_point_id):
        branch_point = get_object_or_404(BranchPoint, pk=branch_point_id)
        story        = branch_point.chapter.story

        if story.author != request.user:
            return Response({'detail': 'Only the author can close voting.'}, status=403)

        branch_point.voting_open = False
        branch_point.save(update_fields=['voting_open'])

        winner = branch_point.choices.order_by('-votes_count').first()
        if winner:
            BranchChoice.objects.filter(branch_point=branch_point).update(is_winner=False)
            winner.is_winner = True
            winner.save(update_fields=['is_winner'])

        serializer = BranchPointSerializer(branch_point, context={'request': request})
        return Response(serializer.data)
