from rest_framework import serializers
from .models import BlogCategory, BlogPost, BlogLike, BlogComment


class BlogCategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()

    class Meta:
        model  = BlogCategory
        fields = ['id', 'name', 'slug', 'description', 'post_count', 'created_at']
        read_only_fields = ['slug', 'created_at']

    def get_post_count(self, obj):
        return obj.posts.filter(status=BlogPost.STATUS_PUBLISHED).count()


class BlogPostListSerializer(serializers.ModelSerializer):
    category      = BlogCategorySerializer(read_only=True)
    author_name   = serializers.SerializerMethodField()
    author_role   = serializers.SerializerMethodField()
    tags_list     = serializers.SerializerMethodField()
    like_count    = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model  = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'cover_image',
            'category', 'author_name', 'author_role',
            'status', 'audience', 'tags_list', 'views', 'read_time',
            'like_count', 'comment_count',
            'created_at', 'updated_at',
        ]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def get_author_role(self, obj):
        return getattr(obj.author, 'role', 'se')

    def get_tags_list(self, obj):
        return [t.strip() for t in obj.tags.split(',') if t.strip()] if obj.tags else []

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_comment_count(self, obj):
        return obj.comments.count()


class BlogPostDetailSerializer(BlogPostListSerializer):
    user_liked = serializers.SerializerMethodField()

    class Meta(BlogPostListSerializer.Meta):
        fields = BlogPostListSerializer.Meta.fields + ['content', 'user_liked']

    def get_user_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False


class BlogCommentSerializer(serializers.ModelSerializer):
    author_name   = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    replies       = serializers.SerializerMethodField()

    class Meta:
        model  = BlogComment
        fields = ['id', 'author_name', 'author_avatar', 'content', 'parent',
                  'replies', 'created_at']
        read_only_fields = ['id', 'author_name', 'author_avatar', 'replies', 'created_at']

    def get_author_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_author_avatar(self, obj):
        request = self.context.get('request')
        if hasattr(obj.user, 'avatar') and obj.user.avatar:
            try:
                url = obj.user.avatar.url
                return request.build_absolute_uri(url) if request else url
            except Exception:
                pass
        return None

    def get_replies(self, obj):
        if obj.parent is not None:
            return []
        qs = obj.replies.all()
        return BlogCommentSerializer(qs, many=True, context=self.context).data


class BlogPostWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BlogPost
        fields = [
            'title', 'excerpt', 'content', 'cover_image',
            'category', 'status', 'audience', 'tags',
        ]

    def validate_cover_image(self, value):
        if value and hasattr(value, 'size') and value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError('Cover image must not exceed 2MB.')
        return value

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
