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
    ordering_fields  = ['created_at', 'total_views', 'average_rating', 'total_chapters']
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
        instance = self.get_object()
        # Increment view count
        Story.objects.filter(pk=instance.pk).update(total_views=F('total_views') + 1)
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