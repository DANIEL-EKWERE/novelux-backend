from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.coins.serializers import CreateCheckoutSessionSerializer
from apps.stories.models import Story
from .models import Report, StoryReview, ReportMissingStory
from .serializers import StoryReviewSerializer, CreateReviewSerializer, ReportSerializer, ReportMissingStorySerializer


class StoryReviewsView(APIView):
    """
    GET  /api/stories/<slug>/reviews/          — list reviews
    GET  /api/stories/<slug>/reviews/?rating=recommend
    POST /api/stories/<slug>/reviews/          — create or update review
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get(self, request, slug):
        story  = get_object_or_404(Story, slug=slug)
        rating = request.query_params.get('rating', 'all')

        qs = StoryReview.objects.filter(story=story)\
               .select_related('user')\
               .annotate(likes_count_ann=Count('likes'))

        if rating != 'all':
            qs = qs.filter(rating=rating)

        # Counts for all ratings
        all_reviews      = StoryReview.objects.filter(story=story)
        recommend_count  = all_reviews.filter(rating='recommend').count()
        average_count    = all_reviews.filter(rating='average').count()
        not_good_count   = all_reviews.filter(rating='not_good').count()
        total_count      = all_reviews.count()

        serializer = StoryReviewSerializer(
            qs, many=True, context={'request': request})

        return Response({
            'results':         serializer.data,
            'total_count':     total_count,
            'recommend_count': recommend_count,
            'average_count':   average_count,
            'not_good_count':  not_good_count,
        })

    def post(self, request, slug):
        story = get_object_or_404(Story, slug=slug)

        # Can't review your own story
        if story.author == request.user:
            return Response(
                {'detail': 'You cannot review your own story.'},
                status=status.HTTP_400_BAD_REQUEST)

        serializer = CreateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update if already reviewed, create if not
        review, created = StoryReview.objects.update_or_create(
            story=story,
            user=request.user,
            defaults={
                'rating':  serializer.validated_data['rating'],
                'content': serializer.validated_data.get('content', ''),
            }
        )

        # Update story average rating
        self._update_story_rating(story)

        return Response(
            StoryReviewSerializer(review, context={'request': request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _update_story_rating(self, story):
        """Recalculate story average rating based on reviews."""
        reviews = StoryReview.objects.filter(story=story)
        total   = reviews.count()
        if total == 0:
            story.average_rating = 0
        else:
            # recommend=5, average=3, not_good=1
            score_map = {'recommend': 5, 'average': 3, 'not_good': 1}
            total_score = sum(
                score_map.get(r.rating, 3) for r in reviews)
            # Scale to 5.0
            story.average_rating = round(total_score / total, 1)
        story.save(update_fields=['average_rating'])


class ReviewLikeView(APIView):
    """POST/DELETE /api/stories/<slug>/reviews/<review_id>/like/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug, review_id):
        review = get_object_or_404(StoryReview, pk=review_id,
                                    story__slug=slug)
        review.likes.add(request.user)
        return Response({'likes_count': review.likes_count})

    def delete(self, request, slug, review_id):
        review = get_object_or_404(StoryReview, pk=review_id,
                                    story__slug=slug)
        review.likes.remove(request.user)
        return Response({'likes_count': review.likes_count})


class ReportView(APIView):
    """POST /api/stories/<slug>/reviews/<review_id>/report/"""
    permission_classes = [permissions.IsAuthenticated]



    def post(self, request):
        serializer = ReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        reason = data['reason']
        phone  = data['phone']
        image  = data['image']
        report = Report.objects.create(
            user=request.user,
            reason=reason,
            phone=phone,
            image=image
        )
        return Response({'detail': 'Report reported successfully.'})
    


class ReportMissingStoryView(APIView):
    """POST /api/stories/<slug>/reviews/<review_id>/report/"""
    permission_classes = [permissions.IsAuthenticated]



    def post(self, request):
        serializer = ReportMissingStorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        reason = data['reason']
        phone  = data['phone']
        image  = data['image']
        reportmissingstory = ReportMissingStory.objects.create(
            user=request.user,
            reason=reason,
            phone=phone,
            image=image
        )
        return Response({'detail': 'Missing story reported successfully.'})
  
# 
# ReportMissingStory    