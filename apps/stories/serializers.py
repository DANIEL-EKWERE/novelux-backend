from rest_framework import serializers
from django.utils.text import slugify
from .models import FeaturedAuthor, PromoBanner, Story, Genre, Subgenre, Tag, Bookmark, ReadingProgress, Rating, StoryCharacter, StoryLike
from apps.users.serializers import PublicUserSerializer


class StoryCharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StoryCharacter
        fields = ['id', 'name', 'role', 'age', 'gender', 'description', 'image', 'order']
        read_only_fields = ['id']


class SubgenreSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Subgenre
        fields = ['id', 'name', 'slug', 'genre_id']


class GenreSerializer(serializers.ModelSerializer):
    subgenres = SubgenreSerializer(many=True, read_only=True)

    class Meta:
        model  = Genre
        fields = ['id', 'name', 'slug', 'description', 'cover_image', 'subgenres']


class TagSerializer(serializers.ModelSerializer):
    genre_id   = serializers.IntegerField(source='genre.id',   read_only=True, allow_null=True)
    genre_slug = serializers.CharField(source='genre.slug',    read_only=True, allow_null=True)

    class Meta:
        model  = Tag
        fields = ['id', 'name', 'slug', 'genre_id', 'genre_slug']


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


class StoryListBatchSerializer(serializers.ListSerializer):
    """Loads the related data every StoryListSerializer row needs in a fixed
    handful of queries for the whole list, instead of ~10 queries per story
    (author, genre subgenres, tag genres, characters, chapter and follower
    counts). Works on any queryset or list, so callers needn't remember
    select_related/prefetch_related."""

    def to_representation(self, data):
        from django.db.models import Count, Manager, prefetch_related_objects
        from apps.chapters.models import Chapter
        from apps.users.models import Follow

        stories = list(data.all() if isinstance(data, Manager) else data)
        if not stories:
            return []
        prefetch_related_objects(
            stories,
            'author__author_profile', 'genre__subgenres', 'subgenre',
            'tags__genre', 'story_characters',
        )
        story_ids = {st.pk for st in stories}
        chapter_counts = dict(
            Chapter.objects.filter(story_id__in=story_ids)
            .values('story_id').annotate(n=Count('id')).values_list('story_id', 'n')
        )
        author_ids = {st.author_id for st in stories}
        follower_counts = dict(
            Follow.objects.filter(following_id__in=author_ids)
            .values('following_id').annotate(n=Count('id')).values_list('following_id', 'n')
        )
        for st in stories:
            st._all_chapters_count = chapter_counts.get(st.pk, 0)
            if st.author is not None:
                st.author._followers_count = follower_counts.get(st.author_id, 0)
        return super().to_representation(stories)


class StoryListSerializer(serializers.ModelSerializer):
    author             = PublicUserSerializer(read_only=True)
    genre              = GenreSerializer(read_only=True)
    subgenre           = SubgenreSerializer(read_only=True)
    tags               = TagSerializer(many=True, read_only=True)
    story_characters   = StoryCharacterSerializer(many=True, read_only=True)
    all_chapters_count = serializers.SerializerMethodField()
    can_apply_contract = serializers.SerializerMethodField()
    rejection_reason   = serializers.SerializerMethodField()

    class Meta:
        list_serializer_class = StoryListBatchSerializer
        model  = Story
        fields = [
            'id', 'book_code', 'title', 'slug', 'cover_image', 'synopsis', 'description', 'story_outline',
            'author', 'genre', 'subgenre', 'tags', 'language', 'status',
            'total_views', 'total_chapters', 'total_comments', 'word_count', 'target_word_count',
            'average_rating', 'total_likes', 'is_featured', 'is_editors_pick', 'created_at', 'published_at',
            'free_until', 'is_free_download',
            'all_chapters_count', 'contract_status', 'contract_eligible', 'can_apply_contract',
            'rejection_reason', 'story_characters',
            'age_rating', 'is_explicit',
        ]

    def get_all_chapters_count(self, obj):
        cached = getattr(obj, '_all_chapters_count', None)
        return cached if cached is not None else obj.chapters.count()

    def get_can_apply_contract(self, obj):
        """True when threshold is hit and author hasn't applied yet."""
        return obj.contract_eligible and obj.contract_status == 'none'

    def get_rejection_reason(self, obj):
        """Return the rejection reason when the story's contract was rejected."""
        if obj.contract_status != 'rejected':
            return None
        try:
            app = obj.contract_application
            # CE rejection stores in rejection_reason; SE rejection stores in se_note
            return app.rejection_reason or app.se_note or None
        except Exception:
            return None

class StoryDetailSerializer(serializers.ModelSerializer):
    author           = PublicUserSerializer(read_only=True)
    genre            = GenreSerializer(read_only=True)
    tags             = TagSerializer(many=True, read_only=True)
    story_characters = StoryCharacterSerializer(many=True, read_only=True)
    is_bookmarked    = serializers.SerializerMethodField()
    is_liked         = serializers.SerializerMethodField()
    user_rating      = serializers.SerializerMethodField()
    reading_progress = serializers.SerializerMethodField()

    class Meta:
        model  = Story
        fields = '__all__'

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Bookmark.objects.filter(user=request.user, story=obj).exists()
        return False

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return StoryLike.objects.filter(user=request.user, story=obj).exists()
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
    tag_ids      = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, write_only=True, required=False, source='tags'
    )
    genre_id     = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(), write_only=True, required=False, source='genre'
    )
    subgenre_id  = serializers.PrimaryKeyRelatedField(
        queryset=Subgenre.objects.all(), write_only=True, required=False,
        source='subgenre', allow_null=True,
    )

    class Meta:
        model  = Story
        fields = [
            'title', 'synopsis', 'description', 'story_outline', 'cover_image',
            'genre_id', 'subgenre_id', 'tag_ids',
            'language', 'status', 'update_schedule', 'chapters_per_week',
            'plot_summary', 'gender', 'target_word_count', 'target_audience',
            'characters', 'external_link', 'lock_from_chapter',
            'age_rating', 'is_explicit',
        ]

    def validate_cover_image(self, value):
        if value and hasattr(value, 'size') and value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError('Cover image must not exceed 2MB.')
        return value

    def validate(self, data):
        genre    = data.get('genre')
        subgenre = data.get('subgenre')
        if subgenre and genre and subgenre.genre_id != genre.pk:
            raise serializers.ValidationError(
                {'subgenre_id': 'This subgenre does not belong to the selected genre.'}
            )
        # Explicit content is always age-restricted to 18+, regardless of
        # what the client sent.
        is_explicit = data.get(
            'is_explicit',
            self.instance.is_explicit if self.instance else False,
        )
        if is_explicit:
            data['age_rating'] = '18+'
        return data

    def create(self, validated_data):
        import re
        tags = validated_data.pop('tags', [])
        validated_data['author'] = self.context['request'].user

        clean_title = re.sub(r"[^\w\s-]", "", validated_data['title'])
        base_slug   = slugify(clean_title) or 'story'
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


class FeaturedAuthorSerializer(serializers.ModelSerializer):
    user    = PublicUserSerializer(read_only=True)
    stories = serializers.SerializerMethodField()

    class Meta:
        model  = FeaturedAuthor
        fields = ['id', 'user', 'headline', 'stories']

    def get_stories(self, obj):
        from .models import Story
        stories = Story.objects.exclude(status=Story.STATUS_DRAFT)\
                               .filter(author=obj.user)\
                               .select_related('genre')\
                               .prefetch_related('tags')\
                               .order_by('-total_views')[:5]
        return StoryListSerializer(stories, many=True, context=self.context).data