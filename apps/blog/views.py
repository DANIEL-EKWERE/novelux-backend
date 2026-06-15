from rest_framework import generics, permissions, filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import F
from django.shortcuts import get_object_or_404
from .models import BlogCategory, BlogPost, BlogLike, BlogComment
from .serializers import (
    BlogCategorySerializer,
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    BlogPostWriteSerializer,
    BlogCommentSerializer,
)


class IsSE(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', '') in ('se', 'ce', 'admin')


class BlogCategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = BlogCategorySerializer
    queryset = BlogCategory.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsSE()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class BlogCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BlogCategorySerializer
    queryset = BlogCategory.objects.all()
    lookup_field = 'slug'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsSE()]


class BlogPostListView(generics.ListAPIView):
    serializer_class = BlogPostListSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['title', 'excerpt', 'tags', 'author__username', 'category__name']
    ordering_fields  = ['created_at', 'views', 'read_time']
    ordering         = ['-created_at']

    def get_queryset(self):
        qs = BlogPost.objects.select_related('category', 'author')
        user = self.request.user
        pub = BlogPost.STATUS_PUBLISHED

        if user.is_authenticated and getattr(user, 'role', '') in ('se', 'ce', 'admin'):
            # SE/CE: own drafts + all published
            if self.request.query_params.get('mine') == '1':
                return qs.filter(author=user)
            return qs.filter(status=pub) | qs.filter(author=user)

        if user.is_authenticated:
            # Logged-in authors/readers see published posts of both audiences
            return qs.filter(status=pub)

        # Anonymous visitors only see public-audience published posts
        return qs.filter(status=pub, audience=BlogPost.AUDIENCE_PUBLIC)


class BlogPostCreateView(generics.CreateAPIView):
    serializer_class = BlogPostWriteSerializer
    permission_classes = [IsSE]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class BlogPostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset     = BlogPost.objects.select_related('category', 'author')
    lookup_field = 'slug'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return BlogPostWriteSerializer
        return BlogPostDetailSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsSE()]

    def retrieve(self, request, *args, **kwargs):
        from rest_framework.exceptions import PermissionDenied
        instance = self.get_object()
        # Block anonymous access to authors-only posts
        if (not request.user.is_authenticated
                and instance.audience == BlogPost.AUDIENCE_AUTHORS):
            raise PermissionDenied('This article is for registered authors only.')
        if instance.status == BlogPost.STATUS_PUBLISHED:
            BlogPost.objects.filter(pk=instance.pk).update(views=F('views') + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def blog_toggle_like(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, status=BlogPost.STATUS_PUBLISHED)
    like, created = BlogLike.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return Response({'liked': liked, 'like_count': post.likes.count()})


class BlogCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = BlogCommentSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        post = get_object_or_404(BlogPost, slug=self.kwargs['slug'])
        return BlogComment.objects.filter(post=post, parent__isnull=True).select_related('user').prefetch_related('replies__user')

    def perform_create(self, serializer):
        post = get_object_or_404(BlogPost, slug=self.kwargs['slug'])
        parent_id = self.request.data.get('parent')
        parent = None
        if parent_id:
            parent = get_object_or_404(BlogComment, pk=parent_id, post=post)
        serializer.save(user=self.request.user, post=post, parent=parent)
        if post.author != self.request.user:
            try:
                from apps.notifications.services import create_notification
                name = self.request.user.get_full_name() or self.request.user.username
                label = 'replied to a comment on' if parent else 'commented on'
                create_notification(
                    user=post.author,
                    notification_type='comment',
                    title='New comment on your article',
                    message=f'{name} {label} "{post.title}"',
                    data={'slug': post.slug},
                )
            except Exception:
                pass


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def blog_delete_comment(request, pk):
    comment = get_object_or_404(BlogComment, pk=pk)
    if comment.user != request.user and not getattr(request.user, 'role', '') in ('se', 'ce', 'admin'):
        return Response({'detail': 'Not allowed.'}, status=403)
    comment.delete()
    return Response(status=204)


class BlogImageUploadView(APIView):
    """Inline image upload for the editor — returns a URL to embed."""
    permission_classes = [IsSE]
    parser_classes = [MultiPartParser]

    def post(self, request):
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import os, uuid
        img = request.FILES.get('image')
        if not img:
            return Response({'error': 'No image provided'}, status=400)
        if img.size > 5 * 1024 * 1024:
            return Response({'error': 'Image must be under 5MB'}, status=400)
        ext  = os.path.splitext(img.name)[1].lower() or '.jpg'
        name = f'blog/inline/{uuid.uuid4().hex}{ext}'
        saved = default_storage.save(name, ContentFile(img.read()))
        url = request.build_absolute_uri(default_storage.url(saved))
        return Response({'url': url})
