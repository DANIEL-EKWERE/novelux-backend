# serializers.py
from rest_framework import serializers
from .models import Chapter, ChapterUnlock, ChapterUnlockEarning


class ChapterListSerializer(serializers.ModelSerializer):
    estimated_read_minutes = serializers.ReadOnlyField()
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model  = Chapter
        fields = [
            'id', 'title', 'chapter_number', 'is_locked', 'is_unlocked', 'coin_cost',
            'is_published', 'status', 'views', 'unlocks', 'word_count',
            'estimated_read_minutes', 'created_at',
        ]

    def get_is_unlocked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if not obj.is_locked:
            return True
        if obj.story.author == request.user:
            return True
        # VIP subscription ("access_all_novels") includes every locked chapter
        if getattr(request.user, 'is_vip', False):
            return True
        return ChapterUnlock.objects.filter(user=request.user, chapter=obj).exists()


class ChapterDetailSerializer(serializers.ModelSerializer):
    estimated_read_minutes = serializers.ReadOnlyField()
    is_unlocked            = serializers.SerializerMethodField()

    class Meta:
        model  = Chapter
        fields = '__all__'

    def get_is_unlocked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if not obj.is_locked:
            return True
        if obj.story.author == request.user:
            return True
        # VIP subscription ("access_all_novels") includes every locked chapter
        if getattr(request.user, 'is_vip', False):
            return True
        return ChapterUnlock.objects.filter(user=request.user, chapter=obj).exists()

    def to_representation(self, instance):
        data    = super().to_representation(instance)
        request = self.context.get('request')
        # Hide content if locked and not unlocked
        if instance.is_locked:
            unlocked = self.get_is_unlocked(instance)
            if not unlocked:
                # Return preview (first 200 words)
                words = instance.content.split()
                data['content'] = ' '.join(words[:200]) + '...' if len(words) > 200 else instance.content
                data['is_preview'] = True
        return data


class ChapterCreateUpdateSerializer(serializers.ModelSerializer):
    status = serializers.CharField(required=False)
    chapter_number = serializers.IntegerField(required=False, min_value=1)

    class Meta:
        model  = Chapter
        fields = ['title', 'chapter_number', 'content', 'is_locked',
                  'coin_cost', 'scheduled_at', 'status']

    def validate_status(self, value):
        allowed = {Chapter.STATUS_DRAFT, Chapter.STATUS_SUBMITTED,}
        if value not in allowed:
            raise serializers.ValidationError(
                'Chapters may only be saved as draft or submitted by the author.'
            )
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return attrs

        status = attrs.get('status')
        if status == Chapter.STATUS_SUBMITTED:
            instance = getattr(self, 'instance', None)
            if instance and instance.status not in [Chapter.STATUS_DRAFT, Chapter.STATUS_SE_REVISION]:
                raise serializers.ValidationError(
                    'Only draft or revision chapters may be submitted for review.'
                )

        # On create, a duplicate chapter number would hit the DB unique
        # constraint and 500 — reject it with a clean 400 instead.
        if self.instance is None:
            num  = attrs.get('chapter_number')
            view = self.context.get('view')
            slug = getattr(view, 'kwargs', {}).get('story_slug') if view else None
            if num and slug and Chapter.objects.filter(
                    story__slug=slug, chapter_number=num).exists():
                raise serializers.ValidationError(
                    {'chapter_number': f'Chapter {num} already exists for this story.'}
                )
        return attrs

    def _is_truthy(self, val):
        if isinstance(val, bool):
            return val
        if val is None:
            return False
        return str(val).lower() in ('1', 'true', 'yes', 'on')

    def _publish_intent(self, request):
        # The app sends is_publish; the web editor historically sent
        # is_published — honor either.
        if request is None:
            return False
        data = request.data
        return self._is_truthy(data.get('is_publish', data.get('is_published')))

    def create(self, validated_data):
        # No chapter_number sent → append after the story's highest one
        story = validated_data.get('story')
        if not validated_data.get('chapter_number') and story is not None:
            from django.db.models import Max
            validated_data['chapter_number'] = (
                Chapter.objects.filter(story=story)
                .aggregate(m=Max('chapter_number'))['m'] or 0
            ) + 1

        request = self.context.get('request')
        is_publish = self._publish_intent(request)

        if is_publish:
            validated_data['status'] = Chapter.STATUS_DRAFT
            instance = super().create(validated_data)

            story = instance.story
            story.refresh_from_db(fields=['contract_status'])

            if story.contract_status == 'signed':
                # Contracted author with explicit publish intent → go live now
                instance.status = Chapter.STATUS_PUBLISHED
                instance.is_published = True
                instance.save(update_fields=['status', 'is_published'])
            # Non-contracted author → stays a draft; all held drafts are
            # published in bulk by publish_held_chapters_for_author once
            # the contract is signed.

            return instance

        # Ensure saved as draft when not publishing. Pre-contract chapters
        # are ALWAYS drafts, even if the client sent status='submitted' —
        # they must never enter the SE chapter queue.
        if story is not None and story.contract_status != 'signed':
            validated_data['status'] = Chapter.STATUS_DRAFT
        else:
            validated_data['status'] = validated_data.get('status', Chapter.STATUS_DRAFT)
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        request = self.context.get('request')
        is_publish = self._publish_intent(request)

        if is_publish:
            validated_data.pop('status', None)
            inst = super().update(instance, validated_data)

            story = inst.story
            story.refresh_from_db(fields=['contract_status'])

            if story.contract_status == 'signed':
                # Contracted author → publish immediately
                inst.status      = Chapter.STATUS_PUBLISHED
                inst.is_published = True
                inst.save(update_fields=['status', 'is_published'])
            elif inst.status != Chapter.STATUS_DRAFT:
                # Non-contracted author → chapters stay drafts until the
                # contract-signing flow publishes them in bulk via
                # publish_held_chapters_for_author.
                inst.status = Chapter.STATUS_DRAFT
                inst.save(update_fields=['status'])

            return inst

        # Plain save (no publish intent) — keep as draft
        validated_data['status'] = Chapter.STATUS_DRAFT
        validated_data.pop('is_published', None)
        return super().update(instance, validated_data)


class ChapterUnlockEarningSerializer(serializers.ModelSerializer):
    """Editorial's view of a held author earning."""
    author_username = serializers.CharField(source='author.username', read_only=True)
    story_title     = serializers.CharField(source='chapter.story.title', read_only=True)
    chapter_number  = serializers.IntegerField(source='chapter.chapter_number', read_only=True)
    released_by_username = serializers.CharField(
        source='released_by.username', read_only=True, default=None)

    class Meta:
        model  = ChapterUnlockEarning
        fields = ['id', 'author_username', 'story_title', 'chapter_number',
                  'coins', 'coins_spent', 'status', 'note',
                  'released_by_username', 'released_at', 'created_at']
        read_only_fields = fields
