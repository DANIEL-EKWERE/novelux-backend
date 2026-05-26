from rest_framework import serializers
from django.utils.text import slugify
from .models import PromoBanner, Story, Genre, Tag, Bookmark, ReadingProgress, Rating
from apps.users.serializers import PublicUserSerializer


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Genre
        fields = ['id', 'name', 'slug', 'description', 'cover_image']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Tag
        fields = ['id', 'name', 'slug']


# class StoryListSerializer(serializers.ModelSerializer):
#     author = PublicUserSerializer(read_only=True)
#     genre  = GenreSerializer(read_only=True)
#     tags   = TagSerializer(many=True, read_only=True)

#     class Meta:
#         model  = Story
#         fields = [
#             'id', 'title', 'slug', 'cover_image', 'description',
#             'author', 'genre', 'tags', 'language', 'status',
#             'total_views', 'total_chapters', 'total_comments', 'word_count',
#             'average_rating', 'is_featured', 'is_editors_pick', 'created_at',
#         ]

class StoryListSerializer(serializers.ModelSerializer):
    author             = PublicUserSerializer(read_only=True)
    genre              = GenreSerializer(read_only=True)
    tags               = TagSerializer(many=True, read_only=True)
    all_chapters_count = serializers.SerializerMethodField()
    can_apply_contract = serializers.SerializerMethodField()

    class Meta:
        model  = Story
        fields = [
            'id', 'title', 'slug', 'cover_image', 'synopsis', 'description', 'story_outline',
            'author', 'genre', 'tags', 'language', 'status',
            'total_views', 'total_chapters', 'total_comments', 'word_count',
            'average_rating', 'is_featured', 'is_editors_pick', 'created_at',
            'all_chapters_count', 'contract_status', 'contract_eligible', 'can_apply_contract',
        ]

    def get_all_chapters_count(self, obj):
        return obj.chapters.count()

    def get_can_apply_contract(self, obj):
        """True when threshold is hit and author hasn't applied yet."""
        return obj.contract_eligible and obj.contract_status == 'none'

class StoryDetailSerializer(serializers.ModelSerializer):
    author          = PublicUserSerializer(read_only=True)
    genre           = GenreSerializer(read_only=True)
    tags            = TagSerializer(many=True, read_only=True)
    is_bookmarked   = serializers.SerializerMethodField()
    user_rating     = serializers.SerializerMethodField()
    reading_progress= serializers.SerializerMethodField()

    class Meta:
        model  = Story
        fields = '__all__'

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Bookmark.objects.filter(user=request.user, story=obj).exists()
        return False

    def get_user_rating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            r = Rating.objects.filter(user=request.user, story=obj).first()
            return r.score if r else None
        return None

    def get_reading_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            p = ReadingProgress.objects.filter(user=request.user, story=obj).first()
            if p:
                return {'last_chapter': p.last_chapter, 'last_paragraph': p.last_paragraph}
        return None


class StoryCreateUpdateSerializer(serializers.ModelSerializer):
    tag_ids  = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, write_only=True, required=True, source='tags'
    )
    genre_id = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(), write_only=True, required=False, source='genre'
    )

    class Meta:
        model  = Story
        fields = [
            'title', 'synopsis', 'description', 'story_outline', 'cover_image', 'genre_id', 'tag_ids',
            'language', 'status', 'is_exclusive', 'update_schedule', 'plot_summary', 'gender',
            'target_word_count', 'target_audience', 'characters', 'external_link',
        ]

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Please select at least one tag for your story.')
        return value

    def create(self, validated_data):
        import re
        tags = validated_data.pop('tags', [])
        validated_data['author'] = self.context['request'].user

        # Strip ALL non-alphanumeric chars (apostrophes, quotes, etc.) before slugifying
        clean_title = re.sub(r"[^\w\s-]", "", validated_data['title'])
        base_slug   = slugify(clean_title) or 'story'

        # Ensure uniqueness
        slug, n = base_slug, 1
        while Story.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{n}"
            n   += 1

        validated_data['slug'] = slug
        story = Story.objects.create(**validated_data)
        story.tags.set(tags)
        return story

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance


class RatingSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)

    class Meta:
        model  = Rating
        fields = ['id', 'user', 'score', 'review', 'created_at']
        read_only_fields = ['user', 'created_at']


class PromoBannerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = PromoBanner
        fields = ['id', 'title', 'image', 'slug', 'color']  # ← 'image' not 'image_url'

    def get_image(self, obj):
        request = self.context.get('request')
        return obj.get_image_url(request)