# from rest_framework import generics, permissions, filters, status
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from django_filters.rest_framework import DjangoFilterBackend
# from django.shortcuts import get_object_or_404
# from django.db.models import F
# from .models import BookRequest, PromoBanner, Story, Genre, Tag, Bookmark, ReadingProgress, Rating
# from .serializers import (
#     PromoBannerSerializer, PromoBannerSerializer, StoryListSerializer, StoryDetailSerializer, StoryCreateUpdateSerializer,
#     GenreSerializer, TagSerializer, RatingSerializer
# )
# from .filters import StoryFilter
# from apps.users.permissions import IsAuthorOrReadOnly
# from apps.users.models import UserPreferences
# from apps.users.serializers import UserPreferencesSerializer


# class StoryListCreateView(generics.ListCreateAPIView):
#     queryset         = Story.objects.select_related('author', 'genre').prefetch_related('tags')
#     filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_class  = StoryFilter
#     search_fields    = ['title', 'description', 'author__username', 'tags__name']
#     ordering_fields  = ['created_at', 'total_views', 'average_rating', 'total_chapters']
#     ordering         = ['-created_at']

#     def get_serializer_class(self):
#         if self.request.method == 'POST':
#             return StoryCreateUpdateSerializer
#         return StoryListSerializer

#     def get_permissions(self):
#         if self.request.method == 'POST':
#             return [permissions.IsAuthenticated()]
#         return [permissions.AllowAny()]

#     def get_queryset(self):
#         qs = super().get_queryset()
#         if self.request.method == 'GET':
#             if self.request.user.is_authenticated and story.author == self.request.user:
#                 return qs  # Authors can see all their stories, including drafts:
#             qs = qs.exclude(status=Story.STATUS_DRAFT)
#         return qs


# class StoryDetailView(generics.RetrieveUpdateDestroyAPIView):
#     queryset     = Story.objects.select_related('author', 'genre').prefetch_related('tags')
#     lookup_field = 'slug'

#     def get_serializer_class(self):
#         if self.request.method in ('PUT', 'PATCH'):
#             return StoryCreateUpdateSerializer
#         return StoryDetailSerializer

#     def get_permissions(self):
#         if self.request.method in ('PUT', 'PATCH', 'DELETE'):
#             return [IsAuthorOrReadOnly()]
#         return [permissions.AllowAny()]

#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         # Increment view count
#         Story.objects.filter(pk=instance.pk).update(total_views=F('total_views') + 1)
#         serializer = self.get_serializer(instance)
#         return Response(serializer.data)


# # class MyStoriesView(generics.ListAPIView):
# #     serializer_class   = StoryListSerializer
# #     permission_classes = [permissions.IsAuthenticated]

# #     def get_queryset(self):
# #         return Story.objects.filter(author=self.request.user).select_related('genre').prefetch_related('tags')


# # class TrendingStoriesView(generics.ListAPIView):
# #     serializer_class = StoryListSerializer

# #     def get_queryset(self):
# #         return Story.objects.exclude(status=Story.STATUS_DRAFT).order_by('-total_views')[:20]


# # class FeaturedStoriesView(generics.ListAPIView):
# #     serializer_class = StoryListSerializer

# #     def get_queryset(self):
# #         return Story.objects.filter(is_featured=True).exclude(status=Story.STATUS_DRAFT)


# # class WorldFamousStoriesView(generics.ListAPIView):
# #     serializer_class = StoryListSerializer

# #     def get_queryset(self):
# #         if self.request.user.is_authenticated:
# #             gender = UserPreferences.objects.get(user=self.request.user).gender
# #         else:
# #             gender = None
# #         if gender is not None:
# #             return Story.objects.filter(is_world_famous=True, gender=gender).exclude(status=Story.STATUS_DRAFT)
# #         return Story.objects.filter(is_world_famous=True).exclude(status=Story.STATUS_DRAFT)


# # class CompletedStoriesView(generics.ListAPIView):
# #     serializer_class = StoryListSerializer

# #     def get_queryset(self):
# #         return Story.objects.filter(is_completed=True).exclude(status=Story.STATUS_DRAFT)
    
    
# # class AfricanFolktaleStoriesView(generics.ListAPIView):
# #     serializer_class = StoryListSerializer

# #     def get_queryset(self):
# #         return Story.objects.filter(is_african_folktale=True).exclude(status=Story.STATUS_DRAFT)




# # class FreeDownloadStoriesView(generics.ListAPIView):
# #     serializer_class = StoryListSerializer

# #     def get_queryset(self):
# #         return Story.objects.filter(is_free_download=True).exclude(status=Story.STATUS_DRAFT)


# # class EditorsPickView(generics.ListAPIView):
# #     serializer_class = StoryListSerializer

# #     def get_queryset(self):
# #         return Story.objects.filter(is_editors_pick=True).exclude(status=Story.STATUS_DRAFT)


# def published_stories():
#     """Base queryset: excludes drafts, eager-loads relations."""
#     return Story.objects.exclude(status=Story.STATUS_DRAFT)\
#                         .select_related('genre')\
#                         .prefetch_related('tags')


# def apply_gender_filter(qs, user):
#     """Filter queryset by user gender preference if available."""
#     if user.is_authenticated:
#         prefs = UserPreferences.objects.filter(user=user).first()
#         gender = prefs.gender if prefs else None
#         if gender is not None:
#             return qs.filter(gender=gender)
#     return qs

# from django.db.models import Count

# class MyStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return Story.objects.filter(author=self.request.user)\
#                             .annotate(real_count=Count('chapters'))\
#                             .select_related('genre')\
#                             .prefetch_related('tags')\
#                             .order_by('-created_at')


# class TrendingStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         qs = published_stories().order_by('-total_views')
#         return apply_gender_filter(qs, self.request.user)[:20]


# class FeaturedStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         qs = published_stories().filter(is_featured=True)
#         return apply_gender_filter(qs, self.request.user)


# class WorldFamousStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         qs = published_stories().filter(is_world_famous=True)
#         return apply_gender_filter(qs, self.request.user)


# class CompletedStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         qs = published_stories().filter(is_completed=True)
#         return apply_gender_filter(qs, self.request.user)


# class AfricanFolktaleStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         qs = published_stories().filter(is_african_folktale=True)
#         return apply_gender_filter(qs, self.request.user)


# class FreeDownloadStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         qs = published_stories().filter(is_free_download=True)
#         return apply_gender_filter(qs, self.request.user)


# class EditorsPickView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         qs = published_stories().filter(is_editors_pick=True)
#         return apply_gender_filter(qs, self.request.user)
    
    

# class BookmarkView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, slug):
#         story = get_object_or_404(Story, slug=slug)
#         _, created = Bookmark.objects.get_or_create(user=request.user, story=story)
#         return Response({'bookmarked': True}, status=201 if created else 200)

#     def delete(self, request, slug):
#         story = get_object_or_404(Story, slug=slug)
#         Bookmark.objects.filter(user=request.user, story=story).delete()
#         return Response({'bookmarked': False}, status=204)


# class MyBookmarksView(generics.ListAPIView):
#     serializer_class   = StoryListSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return Story.objects.filter(bookmarked_by__user=self.request.user)


# class UpdateReadingProgressView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, slug):
#         story = get_object_or_404(Story, slug=slug)
#         progress, _ = ReadingProgress.objects.get_or_create(user=request.user, story=story)
#         progress.last_chapter   = request.data.get('last_chapter', progress.last_chapter)
#         progress.last_paragraph = request.data.get('last_paragraph', progress.last_paragraph)
#         progress.save()
#         return Response({'detail': 'Progress saved.'})


# class RateStoryView(generics.CreateAPIView):
#     serializer_class   = RatingSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def perform_create(self, serializer):
#         story = get_object_or_404(Story, slug=self.kwargs['slug'])
#         Rating.objects.filter(user=self.request.user, story=story).delete()
#         serializer.save(user=self.request.user, story=story)


# class GenreListView(generics.ListAPIView):
#     serializer_class = GenreSerializer
#     queryset         = Genre.objects.all()
#     pagination_class = None


# class TagListView(generics.ListAPIView):
#     serializer_class = TagSerializer
#     queryset         = Tag.objects.all()
#     pagination_class = None


# class PromoBannersView(APIView):
#     # \"\"\"GET /api/stories/banners/\"\"\"
#     permission_classes = [permissions.AllowAny]
 
#     def get(self, request):
#         banners = PromoBanner.objects.filter(is_active=True)
#         if not banners.exists():
#             # Fallback hardcoded
#             return Response([
#                 {'id': 1, 'title': 'New Arrivals This Week',
#                  'image': None, 'slug': '', 'color': '#C15F3C'},
#                 {'id': 2, 'title': 'Top Romance Picks',
#                  'image': None, 'slug': '', 'color': '#6B3FA0'},
#                 {'id': 3, 'title': 'African Bestsellers',
#                  'image': None, 'slug': '', 'color': '#1B5E20'},
#             ])
#         serializer = PromoBannerSerializer(banners, many=True,
#                                            context={'request': request})
#         return Response(serializer.data)

# # class PromoBannersView(APIView):
# #     # \"\"\"GET /api/stories/banners/ — promotional banners for home carousel\"\"\"
# #     permission_classes = [permissions.AllowAny]
 
# #     def get(self, request):
# #         # Hardcoded for now — replace with DB model when ready
# #         banners = [
# #             {
# #                 'id':    1,
# #                 'image': None,   # or absolute URL to banner image
# #                 'title': 'New Arrivals This Week',
# #                 'slug':  '',     # story slug to navigate to on tap
# #                 'color': '#C15F3C',
# #             },
# #             {
# #                 'id':    2,
# #                 'image': None,
# #                 'title': 'Top Romance Picks',
# #                 'slug':  '',
# #                 'color': '#6B3FA0',
# #             },
# #             {
# #                 'id':    3,
# #                 'image': None,
# #                 'title': 'African Bestsellers',
# #                 'slug':  '',
# #                 'color': '#1B5E20',
# #             },
# #         ]
# #         return Response(banners)


 
 
# class BookRequestView(APIView):
#     # \"\"\"POST /api/stories/request/\"\"\"
#     permission_classes = [permissions.AllowAny]
 
#     def post(self, request):
#         title  = request.data.get('title', '').strip()
#         author = request.data.get('author', '').strip()
#         if not title:
#             return Response({'detail': 'title required'},
#                             status=status.HTTP_400_BAD_REQUEST)
#         BookRequest.objects.create(
#             title=title,
#             author=author,
#             requested_by=request.user if request.user.is_authenticated else None,
#         )
#         return Response({'detail': 'Request received. Thank you!'})

# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def apply_for_contract(request, slug):
#     """
#     POST /api/stories/<slug>/apply-contract/
#     Author manually applies for a contract once their story hits threshold.
#     """
#     from django.shortcuts import get_object_or_404
#     from apps.chapters.models import Chapter

#     story = get_object_or_404(Story, slug=slug, author=request.user)

#     if not story.contract_eligible:
#         return Response(
#             {'detail': 'This story has not yet reached the chapter threshold.'},
#             status=400,
#         )
#     if story.contract_status != 'none':
#         return Response(
#             {'detail': 'A contract application already exists for this story.'},
#             status=400,
#         )

#     # Flip all pre-review chapters into the SE queue
#     pre_review = [Chapter.STATUS_DRAFT, Chapter.STATUS_SUBMITTED]
#     Chapter.objects.filter(story=story, status__in=pre_review).update(
#         status=Chapter.STATUS_PENDING_REVIEW
#     )

#     # Create ContractApplication and lock the story
#     from apps.editorial.models import ContractApplication, AuthorEditorLink

#     def _resolve_se(author):
#         try:
#             link = AuthorEditorLink.objects.select_related('assigned_se').get(author=author)
#             return link.assigned_se
#         except AuthorEditorLink.DoesNotExist:
#             return None

#     ContractApplication.objects.get_or_create(
#         story=story,
#         defaults={
#             'author': request.user,
#             'assigned_se': _resolve_se(request.user),
#             'status': ContractApplication.STATUS_PENDING,
#         }
#     )

#     Story.objects.filter(pk=story.pk).update(contract_status='under_review')

#     return Response({'status': 'applied', 'contract_status': 'under_review'})










from rest_framework import generics, permissions, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import F
from .models import BookRequest, PromoBanner, Story, Genre, Tag, Bookmark, ReadingProgress, Rating
from .serializers import (
    PromoBannerSerializer, PromoBannerSerializer, StoryListSerializer, StoryDetailSerializer, StoryCreateUpdateSerializer,
    GenreSerializer, TagSerializer, RatingSerializer
)
from .filters import StoryFilter
from apps.users.permissions import IsAuthorOrReadOnly
from apps.users.models import UserPreferences
from apps.users.serializers import UserPreferencesSerializer


class StoryListCreateView(generics.ListCreateAPIView):
    queryset         = Story.objects.select_related('author', 'genre').prefetch_related('tags')
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class  = StoryFilter
    search_fields    = ['title', 'description', 'author__username', 'tags__name']
    ordering_fields  = ['created_at', 'total_views', 'average_rating', 'total_chapters', 'total_comments', 'word_count', 'total_tips', 'status']
    ordering         = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return StoryCreateUpdateSerializer
        return StoryListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.method == 'GET':
            if self.request.user.is_authenticated and story.author == self.request.user:
                return qs  # Authors can see all their stories, including drafts:
            qs = qs.exclude(status=Story.STATUS_DRAFT)
        return qs


class StoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset     = Story.objects.select_related('author', 'genre').prefetch_related('tags')
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return StoryCreateUpdateSerializer
        return StoryDetailSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAuthorOrReadOnly()]
        return [permissions.AllowAny()]

    def retrieve(self, request, *args, **kwargs):
        from datetime import date
        from django.db.models import F
        from .models import StoryDailyStats, UserStoryInteraction

        instance = self.get_object()
        Story.objects.filter(pk=instance.pk).update(total_views=F('total_views') + 1)

        # Record daily view (powers time-windowed rankings)
        today = date.today()
        StoryDailyStats.objects.get_or_create(story=instance, date=today)
        StoryDailyStats.objects.filter(story=instance, date=today).update(
            views=F('views') + 1
        )

        # Record user interaction (powers recommendations)
        if request.user.is_authenticated:
            UserStoryInteraction.objects.update_or_create(
                user=request.user, story=instance,
                defaults={'viewed': True},
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# class MyStoriesView(generics.ListAPIView):
#     serializer_class   = StoryListSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return Story.objects.filter(author=self.request.user).select_related('genre').prefetch_related('tags')


# class TrendingStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         return Story.objects.exclude(status=Story.STATUS_DRAFT).order_by('-total_views')[:20]


# class FeaturedStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         return Story.objects.filter(is_featured=True).exclude(status=Story.STATUS_DRAFT)


# class WorldFamousStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         if self.request.user.is_authenticated:
#             gender = UserPreferences.objects.get(user=self.request.user).gender
#         else:
#             gender = None
#         if gender is not None:
#             return Story.objects.filter(is_world_famous=True, gender=gender).exclude(status=Story.STATUS_DRAFT)
#         return Story.objects.filter(is_world_famous=True).exclude(status=Story.STATUS_DRAFT)


# class CompletedStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         return Story.objects.filter(is_completed=True).exclude(status=Story.STATUS_DRAFT)
    
    
# class AfricanFolktaleStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         return Story.objects.filter(is_african_folktale=True).exclude(status=Story.STATUS_DRAFT)




# class FreeDownloadStoriesView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         return Story.objects.filter(is_free_download=True).exclude(status=Story.STATUS_DRAFT)


# class EditorsPickView(generics.ListAPIView):
#     serializer_class = StoryListSerializer

#     def get_queryset(self):
#         return Story.objects.filter(is_editors_pick=True).exclude(status=Story.STATUS_DRAFT)


def published_stories():
    """Base queryset: excludes drafts, eager-loads relations."""
    return Story.objects.exclude(status=Story.STATUS_DRAFT)\
                        .select_related('genre')\
                        .prefetch_related('tags')


def apply_gender_filter(qs, user):
    """Filter queryset by user gender preference if available."""
    if user.is_authenticated:
        prefs = UserPreferences.objects.filter(user=user).first()
        gender = prefs.gender if prefs else None
        if gender is not None:
            return qs.filter(gender=gender)
    return qs

from django.db.models import Count

class MyStoriesView(generics.ListAPIView):
    serializer_class = StoryListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Story.objects.filter(author=self.request.user)\
                            .annotate(real_count=Count('chapters'))\
                            .select_related('genre')\
                            .prefetch_related('tags')\
                            .order_by('-created_at')


class TrendingStoriesView(generics.ListAPIView):
    serializer_class = StoryListSerializer

    def get_queryset(self):
        qs = published_stories().order_by('-total_views')
        return apply_gender_filter(qs, self.request.user)[:20]


class FeaturedStoriesView(generics.ListAPIView):
    serializer_class = StoryListSerializer

    def get_queryset(self):
        qs = published_stories().filter(is_featured=True)
        return apply_gender_filter(qs, self.request.user)


class WorldFamousStoriesView(generics.ListAPIView):
    serializer_class = StoryListSerializer

    def get_queryset(self):
        qs = published_stories().filter(is_world_famous=True)
        return apply_gender_filter(qs, self.request.user)


class CompletedStoriesView(generics.ListAPIView):
    serializer_class = StoryListSerializer

    def get_queryset(self):
        qs = published_stories().filter(is_completed=True)
        return apply_gender_filter(qs, self.request.user)


class AfricanFolktaleStoriesView(generics.ListAPIView):
    serializer_class = StoryListSerializer

    def get_queryset(self):
        qs = published_stories().filter(is_african_folktale=True)
        return apply_gender_filter(qs, self.request.user)


class FreeDownloadStoriesView(generics.ListAPIView):
    serializer_class = StoryListSerializer

    def get_queryset(self):
        qs = published_stories().filter(is_free_download=True)
        return apply_gender_filter(qs, self.request.user)


class EditorsPickView(generics.ListAPIView):
    serializer_class = StoryListSerializer

    def get_queryset(self):
        qs = published_stories().filter(is_editors_pick=True)
        return apply_gender_filter(qs, self.request.user)
    
    

class BookmarkView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        story = get_object_or_404(Story, slug=slug)
        _, created = Bookmark.objects.get_or_create(user=request.user, story=story)
        return Response({'bookmarked': True}, status=201 if created else 200)

    def delete(self, request, slug):
        story = get_object_or_404(Story, slug=slug)
        Bookmark.objects.filter(user=request.user, story=story).delete()
        return Response({'bookmarked': False}, status=204)


class MyBookmarksView(generics.ListAPIView):
    serializer_class   = StoryListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Story.objects.filter(bookmarked_by__user=self.request.user)


class UpdateReadingProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        story = get_object_or_404(Story, slug=slug)
        progress, _ = ReadingProgress.objects.get_or_create(user=request.user, story=story)
        progress.last_chapter   = request.data.get('last_chapter', progress.last_chapter)
        progress.last_paragraph = request.data.get('last_paragraph', progress.last_paragraph)
        progress.save()
        return Response({'detail': 'Progress saved.'})


class RateStoryView(generics.CreateAPIView):
    serializer_class   = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        story = get_object_or_404(Story, slug=self.kwargs['slug'])
        Rating.objects.filter(user=self.request.user, story=story).delete()
        serializer.save(user=self.request.user, story=story)


class GenreListView(generics.ListAPIView):
    serializer_class = GenreSerializer
    queryset         = Genre.objects.all()
    pagination_class = None


class TagListView(generics.ListAPIView):
    serializer_class = TagSerializer
    queryset         = Tag.objects.all()
    pagination_class = None


class PromoBannersView(APIView):
    # \"\"\"GET /api/stories/banners/\"\"\"
    permission_classes = [permissions.AllowAny]
 
    def get(self, request):
        banners = PromoBanner.objects.filter(is_active=True)
        if not banners.exists():
            # Fallback hardcoded
            return Response([
                {'id': 1, 'title': 'New Arrivals This Week',
                 'image': None, 'slug': '', 'color': '#C15F3C'},
                {'id': 2, 'title': 'Top Romance Picks',
                 'image': None, 'slug': '', 'color': '#6B3FA0'},
                {'id': 3, 'title': 'African Bestsellers',
                 'image': None, 'slug': '', 'color': '#1B5E20'},
            ])
        serializer = PromoBannerSerializer(banners, many=True,
                                           context={'request': request})
        return Response(serializer.data)

# class PromoBannersView(APIView):
#     # \"\"\"GET /api/stories/banners/ — promotional banners for home carousel\"\"\"
#     permission_classes = [permissions.AllowAny]
 
#     def get(self, request):
#         # Hardcoded for now — replace with DB model when ready
#         banners = [
#             {
#                 'id':    1,
#                 'image': None,   # or absolute URL to banner image
#                 'title': 'New Arrivals This Week',
#                 'slug':  '',     # story slug to navigate to on tap
#                 'color': '#C15F3C',
#             },
#             {
#                 'id':    2,
#                 'image': None,
#                 'title': 'Top Romance Picks',
#                 'slug':  '',
#                 'color': '#6B3FA0',
#             },
#             {
#                 'id':    3,
#                 'image': None,
#                 'title': 'African Bestsellers',
#                 'slug':  '',
#                 'color': '#1B5E20',
#             },
#         ]
#         return Response(banners)


 
 
class BookRequestView(APIView):
    # \"\"\"POST /api/stories/request/\"\"\"
    permission_classes = [permissions.AllowAny]
 
    def post(self, request):
        title  = request.data.get('title', '').strip()
        author = request.data.get('author', '').strip()
        if not title:
            return Response({'detail': 'title required'},
                            status=status.HTTP_400_BAD_REQUEST)
        BookRequest.objects.create(
            title=title,
            author=author,
            requested_by=request.user if request.user.is_authenticated else None,
        )
        return Response({'detail': 'Request received. Thank you!'})

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_contract(request, slug):
    """
    POST /api/stories/<slug>/apply-contract/
    Author manually applies for a contract once their story hits threshold.
    """
    from django.shortcuts import get_object_or_404
    from apps.chapters.models import Chapter

    story = get_object_or_404(Story, slug=slug, author=request.user)

    # KYC must be approved before a contract can be applied for
    from apps.users.models import AuthorKYC
    try:
        kyc = AuthorKYC.objects.get(user=request.user)
        if kyc.status != AuthorKYC.STATUS_APPROVED:
            status_msg = {
                AuthorKYC.STATUS_PENDING:  'Your identity verification is still under review. Please wait for it to be approved before applying.',
                AuthorKYC.STATUS_REJECTED: 'Your identity verification was rejected. Please update and resubmit your KYC before applying.',
            }.get(kyc.status, 'Your identity verification is not yet approved.')
            return Response({'detail': status_msg}, status=400)
    except AuthorKYC.DoesNotExist:
        return Response(
            {'detail': 'You must complete identity verification (KYC) before applying for a contract. Go to your dashboard to submit your details.'},
            status=400,
        )

    if not story.contract_eligible:
        return Response(
            {'detail': 'This story has not yet reached the chapter threshold.'},
            status=400,
        )
    if story.contract_status != 'none':
        return Response(
            {'detail': 'A contract application already exists for this story.'},
            status=400,
        )

    # Flip all pre-review chapters into the SE queue
    pre_review = [Chapter.STATUS_DRAFT, Chapter.STATUS_SUBMITTED]
    Chapter.objects.filter(story=story, status__in=pre_review).update(
        status=Chapter.STATUS_PENDING_REVIEW
    )

    # Create ContractApplication and lock the story
    from apps.editorial.models import ContractApplication, AuthorEditorLink

    def _resolve_se(author):
        try:
            link = AuthorEditorLink.objects.select_related('assigned_se').get(author=author)
            return link.assigned_se
        except AuthorEditorLink.DoesNotExist:
            return None

    ContractApplication.objects.get_or_create(
        story=story,
        defaults={
            'author': request.user,
            'assigned_se': _resolve_se(request.user),
            'status': ContractApplication.STATUS_PENDING,
        }
    )

    Story.objects.filter(pk=story.pk).update(contract_status='under_review')

    try:
        from apps.notifications.services import on_contract_applied
        on_contract_applied(request.user, story)
    except Exception:
        pass

    return Response({'status': 'applied', 'contract_status': 'under_review'})


# ── Update Calendar ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def story_update_calendar(request, slug):
    """GET /api/stories/<slug>/update-calendar/?year=&month=
    Returns published-chapter dates and weekly target stats for the given month.
    Accessible by the story author and their assigned SE.
    """
    import calendar as cal_mod
    from datetime import date, timedelta
    from apps.chapters.models import Chapter

    story = get_object_or_404(Story, slug=slug)

    user = request.user
    is_author = story.author == user
    is_se = False
    if not is_author:
        try:
            from apps.editorial.models import AuthorEditorLink
            AuthorEditorLink.objects.get(author=story.author, assigned_se=user)
            is_se = True
        except Exception:
            pass
    if not is_author and not is_se:
        return Response({'detail': 'Not authorized.'}, status=403)

    now = date.today()
    try:
        year  = int(request.query_params.get('year',  now.year))
        month = int(request.query_params.get('month', now.month))
        if not (1 <= month <= 12):
            raise ValueError
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid year/month.'}, status=400)

    chapters_qs = story.chapters.filter(
        is_published=True,
        created_at__year=year,
        created_at__month=month,
    ).values('id', 'chapter_number', 'title', 'created_at')

    day_map = {}
    for ch in chapters_qs:
        d = ch['created_at'].date().isoformat()
        day_map.setdefault(d, []).append({
            'id':             ch['id'],
            'chapter_number': ch['chapter_number'],
            'title':          ch['title'],
        })

    first_day = date(year, month, 1)
    last_day  = date(year, month, cal_mod.monthrange(year, month)[1])
    target    = story.chapters_per_week or 0

    weeks = []
    cur = first_day - timedelta(days=first_day.weekday())
    while cur <= last_day:
        w_start = cur
        w_end   = cur + timedelta(days=6)
        published = sum(
            1 for d_str in day_map
            if w_start <= date.fromisoformat(d_str) <= w_end
        )
        weeks.append({
            'start':     w_start.isoformat(),
            'end':       w_end.isoformat(),
            'published': published,
            'target':    target,
            'met':       target > 0 and published >= target,
        })
        cur += timedelta(weeks=1)

    total_published = sum(len(v) for v in day_map.values())
    weeks_in_month  = len(weeks)
    month_target    = target * weeks_in_month

    return Response({
        'story': {
            'slug':              story.slug,
            'title':             story.title,
            'chapters_per_week': story.chapters_per_week,
            'update_schedule':   story.update_schedule,
        },
        'year':  year,
        'month': month,
        'published_dates': list(day_map.keys()),
        'day_map':         {d: v for d, v in day_map.items()},
        'weeks':           weeks,
        'month_summary': {
            'published': total_published,
            'target':    month_target,
            'met':       month_target > 0 and total_published >= month_target,
        },
    })


# ── Home Section Views ─────────────────────────────────────────────────────────

from datetime import date, timedelta
from django.db.models import Q, Sum
from django.utils.timezone import now
from .models import FeaturedAuthor, StoryDailyStats, UserStoryInteraction
from .serializers import FeaturedAuthorSerializer


class ShortStoriesView(generics.ListAPIView):
    """GET /api/stories/short-stories/
    Stories with a target word count of 50,000–80,000 (the short-story tier
    authors select at creation time), ordered by rating then views."""
    serializer_class = StoryListSerializer

    def get_queryset(self):
        qs = published_stories()\
            .filter(target_word_count='50,000 – 80,000')\
            .order_by('-average_rating', '-total_views')
        return apply_gender_filter(qs, self.request.user)


class NewArrivalsView(generics.ListAPIView):
    """GET /api/stories/new-arrivals/
    Stories published in the last 30 days, newest first."""
    serializer_class = StoryListSerializer

    def get_queryset(self):
        cutoff = now() - timedelta(days=30)
        qs = published_stories()\
            .filter(published_at__gte=cutoff)\
            .order_by('-published_at')
        return apply_gender_filter(qs, self.request.user)


class RecommendedForYouView(generics.ListAPIView):
    """GET /api/stories/recommended/
    Personalised feed based on user interaction history and preferred genres.
    Falls back to trending for unauthenticated users."""
    serializer_class   = StoryListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        qs   = published_stories()

        if user.is_authenticated:
            # Genres from stories the user has actually interacted with
            interacted_genre_ids = Story.objects.filter(
                user_interactions__user=user,
                genre__isnull=False,
            ).values_list('genre_id', flat=True).distinct()

            # Genres from the user's saved preferences
            preferred_slugs    = getattr(user, 'preferred_genres', []) or []
            preferred_genre_ids = Genre.objects.filter(
                slug__in=preferred_slugs
            ).values_list('id', flat=True)

            all_genre_ids = list(set(list(interacted_genre_ids) + list(preferred_genre_ids)))

            # Exclude stories the user has already fully read
            read_story_ids = UserStoryInteraction.objects.filter(
                user=user, completed=True
            ).values_list('story_id', flat=True)

            if all_genre_ids:
                qs = qs.filter(genre_id__in=all_genre_ids)\
                       .exclude(id__in=read_story_ids)\
                       .order_by('-total_views')
            else:
                qs = qs.exclude(id__in=read_story_ids)\
                       .order_by('-total_views')

            return apply_gender_filter(qs, user)[:20]

        return qs.order_by('-total_views')[:20]


class FreeDiscountView(generics.ListAPIView):
    """GET /api/stories/free-discount/
    Stories that are permanently free (is_free_download) or temporarily free
    (free_until is in the future), ordered by free window expiry then recency."""
    serializer_class = StoryListSerializer

    def get_queryset(self):
        qs = published_stories().filter(
            Q(free_until__gt=now()) | Q(is_free_download=True)
        ).order_by('-free_until', '-created_at')
        return apply_gender_filter(qs, self.request.user)


class RankingsView(generics.ListAPIView):
    """GET /api/stories/rankings/?period=daily|weekly|monthly|all-time
    Returns top 50 stories ranked by views in the requested window.
    Daily/weekly/monthly use StoryDailyStats aggregates; all-time uses total_views."""
    serializer_class = StoryListSerializer

    def get_queryset(self):
        period = self.request.query_params.get('period', 'all-time')
        qs     = published_stories()

        if period == 'all-time':
            qs = qs.order_by('-total_views')
        else:
            today = date.today()
            if period == 'daily':
                cutoff = today
            elif period == 'weekly':
                cutoff = today - timedelta(days=7)
            else:  # monthly
                cutoff = today - timedelta(days=30)

            qs = qs.annotate(
                period_views=Sum(
                    'daily_stats__views',
                    filter=Q(daily_stats__date__gte=cutoff),
                )
            ).order_by('-period_views', '-total_views')

        return apply_gender_filter(qs, self.request.user)[:50]


class AuthorSpotlightView(APIView):
    """GET /api/stories/author-spotlight/
    Returns the active FeaturedAuthor with their top 5 published stories."""

    def get(self, request):
        featured = FeaturedAuthor.objects.filter(is_active=True)\
                                         .select_related('user')\
                                         .first()
        if not featured:
            return Response({'detail': 'No featured author.'}, status=404)
        serializer = FeaturedAuthorSerializer(featured, context={'request': request})
        return Response(serializer.data)


class ExploreTabView(APIView):
    """GET /api/stories/explore-tab/<tab>/
    Structured content for each genre tab on the Discover page.

    Supported tabs:
      werewolf | billionaire | suspense  →  sections layout  (5 named sections)
      for-her  | for-him                 →  sections layout  (gender-filtered)
      short-fics                         →  genre-grid layout (stories grouped by tag)
      ranking                            →  ranking layout   (ordered list, ?period=)
    """
    permission_classes = [permissions.AllowAny]

    # Tag slugs used to scope genre tabs
    _TAG_MAP = {
        'werewolf':    ['werewolf', 'alpha', 'luna'],
        'billionaire': ['billionaire', 'ceo-office', 'tycoon', 'ceo'],
        'suspense':    ['suspense-horror', 'thriller', 'mystery', 'horror', 'suspense'],
    }

    # Short Fics sub-genre groupings: (slug, emoji, tag_slugs_to_match)
    _SHORT_FICS_GROUPS = [
        ('romance',       'Romance',            '❤️',  ['romance', 'romance-bxg', 'romance-bxb', 'bxg']),
        ('family-drama',  'Family Drama',        '😮',  ['family-drama', 'family', 'family-emotions', 'drama']),
        ('reborn',        'Reborn / After Death','🔁',  ['reborn', 'reborn-after-death', 'second-chance', 'rebirth', 'after-death']),
        ('werewolf',      "Werewolf's World",    '🐺',  ['werewolf', 'alpha', 'luna']),
        ('mafia',         'Mafia',               '🔪',  ['mafia', 'crime', 'mob']),
        ('revenge',       'Revenge',             '🩸',  ['revenge', 'betrayal', 'abuse', 'abuse-bully']),
    ]

    # ── helpers ──────────────────────────────────────────────────────────────

    def _s(self, story, request):
        return StoryListSerializer(story, context={'request': request}).data

    def _sl(self, qs, request, limit=8):
        return StoryListSerializer(
            qs[:limit], many=True, context={'request': request}
        ).data

    def _pinned_ids(self, tab, section):
        """Return ordered list of story PKs pinned to this tab/section by CE/SE."""
        try:
            from apps.editorial.models import ExploreTabPin
            return list(
                ExploreTabPin.objects
                .filter(tab=tab, section=section, is_active=True)
                .order_by('order', '-pinned_at')
                .values_list('story_id', flat=True)
            )
        except Exception:
            return []

    def _make_section(self, name, qs, request, limit=8, slug=None, display='hero', tab=None):
        """
        display values:
          'hero'      → first story is featured hero card, rest go in stories row
          'row'       → all stories in horizontal scroll row (no hero card)
          'hero-list' → all stories in vertical list with desc/views/tag

        If tab is provided, pinned stories are prepended to the section.
        """
        sec_slug = slug or name.lower().replace(' ', '-')

        # Prepend CE/SE-pinned stories when a tab context is given
        if tab:
            pinned_pks = self._pinned_ids(tab, sec_slug)
            if pinned_pks:
                from django.db.models import Case, When, IntegerField
                pinned_qs = Story.objects.filter(
                    pk__in=pinned_pks
                ).select_related('genre').prefetch_related('tags').annotate(
                    pin_order=Case(
                        *[When(pk=pk, then=i) for i, pk in enumerate(pinned_pks)],
                        default=999, output_field=IntegerField()
                    )
                ).order_by('pin_order')
                # Merge: pinned first, then algorithmic (excluding already-pinned)
                algo_pks = list(qs.exclude(pk__in=pinned_pks).values_list('pk', flat=True)[:limit])
                merged_pks = pinned_pks + algo_pks
                qs = Story.objects.filter(pk__in=merged_pks).select_related('genre').prefetch_related('tags').annotate(
                    pin_order=Case(
                        *[When(pk=pk, then=i) for i, pk in enumerate(merged_pks)],
                        default=999, output_field=IntegerField()
                    )
                ).order_by('pin_order')

        items = list(qs[:limit])
        if not items:
            return None
        base = {
            'name':    name,
            'slug':    sec_slug,
            'display': display,
        }
        if display in ('row', 'hero-list'):
            base['featured'] = None
            base['stories']  = self._sl(qs, request, limit=limit)
        else:
            base['featured'] = self._s(items[0], request)
            base['stories']  = self._sl(
                Story.objects.filter(pk__in=[s.pk for s in items[1:]]).select_related('genre').prefetch_related('tags'),
                request,
            )
        return base

    # ── main dispatch ─────────────────────────────────────────────────────────

    def get(self, request, tab):
        qs = published_stories()

        if tab == 'short-fics':
            return self._short_fics(request, qs)
        if tab == 'ranking':
            return self._ranking(request, qs)
        if tab == 'for-her':
            return self._gender_tab(request, qs, 'female', 'for-her')
        if tab == 'for-him':
            return self._gender_tab(request, qs, 'male', 'for-him')
        if tab == 'suspense':
            return self._suspense_tab(request, qs)
        if tab in self._TAG_MAP:
            return self._genre_tab(request, qs, tab)
        return Response({'error': f'Unknown tab: {tab}'}, status=400)

    # ── short-fics: group short stories by sub-genre tag ─────────────────────

    def _short_fics(self, request, qs):
        short_qs = qs.filter(target_word_count='50,000 – 80,000')
        sections = []

        for slug, display_name, emoji, tag_slugs in self._SHORT_FICS_GROUPS:
            stories = short_qs.filter(
                tags__slug__in=tag_slugs
            ).distinct().order_by('-total_views')

            if not stories.exists():
                # Fallback: name-based match
                q = Q()
                for ts in tag_slugs[:2]:
                    q |= Q(tags__name__icontains=ts.replace('-', ' '))
                stories = short_qs.filter(q).distinct().order_by('-total_views')

            if not stories.exists():
                continue

            items = list(stories[:9])
            sections.append({
                'name':     display_name,
                'emoji':    emoji,
                'featured': self._s(items[0], request),
                'stories':  self._sl(
                    Story.objects.filter(pk__in=[s.pk for s in items[1:]]).select_related('genre').prefetch_related('tags'),
                    request,
                ),
            })

        return Response({'tab': 'short-fics', 'layout': 'genre-grid', 'sections': sections})

    # ── genre tabs (werewolf, billionaire, suspense) ──────────────────────────

    def _genre_tab(self, request, qs, tab):
        tag_slugs = self._TAG_MAP[tab]
        gqs = qs.filter(tags__slug__in=tag_slugs).distinct()

        cutoff = now() - timedelta(days=60)

        just_for_you = gqs.filter(Q(is_featured=True) | Q(is_editors_pick=True)).order_by('-total_views')
        if not just_for_you.exists():
            just_for_you = gqs.order_by('-total_views')

        fresh = gqs.filter(published_at__gte=cutoff).order_by('-published_at')
        if not fresh.exists():
            fresh = gqs.order_by('-published_at')

        rolling = gqs.filter(status='ongoing').order_by('-total_views')
        shorts  = gqs.filter(target_word_count='50,000 – 80,000').order_by('-total_views')
        classics = gqs.filter(Q(is_completed=True) | Q(status='completed')).order_by('-total_views')

        sections = [s for s in [
            self._make_section('Just Your Style',        just_for_you, request, slug='just-your-style',   tab=tab),
            self._make_section('Fresh Reads',            fresh,        request, slug='fresh-reads',        tab=tab),
            self._make_section('Still Rolling Out',      rolling,      request, slug='still-rolling-out',  tab=tab),
            self._make_section('Dive into These Shorts', shorts,       request, slug='short-fics',         tab=tab),
            self._make_section('Completed Classics',     classics,     request, slug='completed-classics', tab=tab),
        ] if s]

        return Response({'tab': tab, 'layout': 'sections', 'sections': sections})

    # ── suspense/horror ──────────────────────────────────────────────────────

    def _suspense_tab(self, request, qs):
        tag_slugs = self._TAG_MAP['suspense']
        gqs       = qs.filter(tags__slug__in=tag_slugs).distinct()

        cutoff   = now() - timedelta(days=60)

        editors  = gqs.filter(is_editors_pick=True).order_by('-total_views')
        if not editors.exists():
            editors = gqs.filter(is_featured=True).order_by('-total_views')

        ends     = gqs.filter(Q(is_completed=True) | Q(status='completed')).order_by('-total_views')
        fresh    = gqs.filter(published_at__gte=cutoff).order_by('-published_at')
        if not fresh.exists():
            fresh = gqs.order_by('-published_at')

        trending = gqs.order_by('-total_views')

        # Stars of Tomorrow: newer, less-known stories with some traction
        stars    = gqs.filter(
            is_featured=False, is_editors_pick=False
        ).order_by('-published_at', '-total_views')
        if not stars.exists():
            stars = gqs.order_by('-published_at')

        sections = [s for s in [
            self._make_section("Editor's Picks",    editors,  request, slug='editors-picks',    display='row',       limit=10, tab='suspense'),
            self._make_section('The Ends',           ends,     request, slug='the-ends',          display='row',       limit=10, tab='suspense'),
            self._make_section('Fresh Drops',        fresh,    request, slug='fresh-drops',       display='row',       limit=10, tab='suspense'),
            self._make_section('Trending Up',        trending, request, slug='trending-up',       display='row',       limit=10, tab='suspense'),
            self._make_section('Stars of Tomorrow',  stars,    request, slug='stars-of-tomorrow', display='hero-list', limit=8,  tab='suspense'),
        ] if s]

        return Response({'tab': 'suspense', 'layout': 'sections', 'sections': sections})

    # ── for-her / for-him ─────────────────────────────────────────────────────

    def _gender_tab(self, request, qs, gender, tab):
        gqs = qs.filter(gender=gender)
        if not gqs.exists():
            gqs = qs  # graceful fallback

        cutoff = now() - timedelta(days=60)

        picks = gqs.filter(Q(is_featured=True) | Q(is_editors_pick=True)).order_by('-total_views')
        if not picks.exists():
            picks = gqs.order_by('-total_views')

        fresh    = gqs.filter(published_at__gte=cutoff).order_by('-published_at')
        if not fresh.exists():
            fresh = gqs.order_by('-published_at')

        classics = gqs.filter(Q(is_completed=True) | Q(status='completed')).order_by('-total_views')

        sections = [s for s in [
            self._make_section('Picks for You',      picks,    request, slug='picks-for-you',      tab=tab),
            self._make_section('Fresh Releases',     fresh,    request, slug='fresh-releases',     tab=tab),
            self._make_section('Completed Classics', classics, request, slug='completed-classics', tab=tab),
        ] if s]

        return Response({'tab': tab, 'layout': 'sections', 'sections': sections})

    # ── ranking ───────────────────────────────────────────────────────────────

    def _ranking(self, request, qs):
        week_ago = now() - timedelta(days=7)

        daily_qs   = qs.filter(published_at__gte=week_ago).order_by('-published_at')
        rising_qs  = qs.filter(published_at__gte=week_ago).order_by('-total_views', '-published_at')
        must_read_qs = qs.filter(
            Q(is_featured=True) | Q(is_editors_pick=True)
        ).order_by('-total_views')
        if not must_read_qs.exists():
            must_read_qs = qs.order_by('-total_views')
        popularity_qs = qs.order_by('-total_views', '-total_likes')
        short_qs      = qs.filter(target_word_count='50,000 – 80,000').order_by('-total_views')

        return Response({
            'tab':    'ranking',
            'layout': 'ranking',
            'new_releases': {
                'daily':  self._sl(daily_qs,   request, limit=5),
                'rising': self._sl(rising_qs,  request, limit=5),
            },
            'most_read': {
                'must_read':  self._sl(must_read_qs,   request, limit=5),
                'popularity': self._sl(popularity_qs,  request, limit=5),
            },
            'short_stories': self._sl(short_qs, request, limit=10),
        })


class RankingSectionView(APIView):
    """GET /api/stories/ranking-section/?section=new-releases&filter=daily&page=1
    Paginated list for the Ranking tab "More" screen.
    section: new-releases | most-read
    filter:  daily | rising  (for new-releases)
             must-read | popularity  (for most-read)
    """
    permission_classes = [permissions.AllowAny]

    _PAGE_SIZE = 20

    def get(self, request):
        section     = request.query_params.get('section', 'new-releases')
        filter_type = request.query_params.get('filter', 'daily')
        page        = max(int(request.query_params.get('page', 1)), 1)

        qs       = published_stories()
        week_ago = now() - timedelta(days=7)

        if section == 'new-releases':
            if filter_type == 'rising':
                qs = qs.filter(published_at__gte=week_ago).order_by('-total_views', '-published_at')
            else:  # daily
                qs = qs.filter(published_at__gte=week_ago).order_by('-published_at')
        else:  # most-read
            if filter_type == 'popularity':
                qs = qs.order_by('-total_views', '-total_likes')
            else:  # must-read
                base = qs.filter(Q(is_featured=True) | Q(is_editors_pick=True)).order_by('-total_views')
                qs   = base if base.exists() else qs.order_by('-total_views')

        total = qs.count()
        start = (page - 1) * self._PAGE_SIZE
        end   = start + self._PAGE_SIZE

        return Response({
            'section':  section,
            'filter':   filter_type,
            'page':     page,
            'has_next': end < total,
            'results':  StoryListSerializer(qs[start:end], many=True, context={'request': request}).data,
        })


class GenreTabSectionView(APIView):
    """GET /api/stories/genre-section/?tab=for-her&section=picks-for-you&page=1
    Paginated "More" list for any section inside a genre/gender tab page.
    tab:     for-her | for-him | werewolf | billionaire | suspense
    section: picks-for-you | fresh-releases | completed-classics |
             just-your-style | fresh-reads | still-rolling-out | short-fics
    """
    permission_classes = [permissions.AllowAny]

    _PAGE_SIZE = 20

    _TAG_MAP = {
        'werewolf':    ['werewolf', 'alpha', 'luna'],
        'billionaire': ['billionaire', 'ceo-office', 'tycoon', 'ceo'],
        'suspense':    ['suspense-horror', 'thriller', 'mystery', 'horror', 'suspense'],
    }

    def get(self, request):
        tab     = request.query_params.get('tab', '')
        section = request.query_params.get('section', '')
        page    = max(int(request.query_params.get('page', 1)), 1)

        qs       = published_stories()
        cutoff   = now() - timedelta(days=60)

        # ── scope by tab ─────────────────────────────────────────────────────
        if tab == 'for-her':
            scoped = qs.filter(gender='female')
            qs     = scoped if scoped.exists() else qs
        elif tab == 'for-him':
            scoped = qs.filter(gender='male')
            qs     = scoped if scoped.exists() else qs
        elif tab in self._TAG_MAP:
            qs = qs.filter(tags__slug__in=self._TAG_MAP[tab]).distinct()

        # ── scope by section ─────────────────────────────────────────────────
        if section in ('picks-for-you', 'just-your-style'):
            base = qs.filter(Q(is_featured=True) | Q(is_editors_pick=True)).order_by('-total_views')
            qs   = base if base.exists() else qs.order_by('-total_views')
        elif section in ('fresh-releases', 'fresh-reads', 'fresh-drops'):
            base = qs.filter(published_at__gte=cutoff).order_by('-published_at')
            qs   = base if base.exists() else qs.order_by('-published_at')
        elif section in ('still-rolling-out', 'trending-up'):
            qs = qs.order_by('-total_views')
        elif section in ('completed-classics', 'the-ends'):
            qs = qs.filter(Q(is_completed=True) | Q(status='completed')).order_by('-total_views')
        elif section == 'editors-picks':
            base = qs.filter(is_editors_pick=True).order_by('-total_views')
            qs   = base if base.exists() else qs.filter(is_featured=True).order_by('-total_views')
            if not qs.exists():
                qs = published_stories().filter(tags__slug__in=self._TAG_MAP.get(tab, [])).distinct().order_by('-total_views')
        elif section == 'stars-of-tomorrow':
            base = qs.filter(is_featured=False, is_editors_pick=False).order_by('-published_at', '-total_views')
            qs   = base if base.exists() else qs.order_by('-published_at')
        elif section == 'short-fics':
            qs = qs.filter(target_word_count='50,000 – 80,000').order_by('-total_views')
        else:
            qs = qs.order_by('-total_views')

        total = qs.count()
        start = (page - 1) * self._PAGE_SIZE
        end   = start + self._PAGE_SIZE

        return Response({
            'tab':      tab,
            'section':  section,
            'page':     page,
            'has_next': end < total,
            'results':  StoryListSerializer(qs[start:end], many=True, context={'request': request}).data,
        })


