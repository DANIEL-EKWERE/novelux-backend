# serializers.py
from rest_framework import serializers
from .models import Chapter, ChapterUnlock


class ChapterListSerializer(serializers.ModelSerializer):
    estimated_read_minutes = serializers.ReadOnlyField()
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model  = Chapter
        fields = [
            'id', 'title', 'chapter_number', 'is_locked', 'is_unlocked', 'coin_cost',
            'is_published', 'views', 'unlocks', 'word_count',
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
        return attrs

    def _is_truthy(self, val):
        if isinstance(val, bool):
            return val
        if val is None:
            return False
        return str(val).lower() in ('1', 'true', 'yes', 'on')

    def create(self, validated_data):
        request = self.context.get('request')
        is_publish = False
        if request is not None:
            is_publish = self._is_truthy(request.data.get('is_publish'))

        # Default to draft unless explicit publish flag provided
        if is_publish:
            # create instance then mark published
            instance = super().create(validated_data)
            instance.status = Chapter.STATUS_PUBLISHED
            instance.is_published = True
            instance.save(update_fields=['status', 'is_published'])
            return instance

        # Ensure saved as draft when not publishing
        validated_data['status'] = validated_data.get('status', Chapter.STATUS_DRAFT)
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        request = self.context.get('request')
        is_publish = False
        if request is not None:
            is_publish = self._is_truthy(request.data.get('is_publish'))

        if is_publish:
            # Remove status from validated_data to avoid validate_status rejecting 'published'
            validated_data.pop('status', None)
            inst = super().update(instance, validated_data)
            inst.status = Chapter.STATUS_PUBLISHED
            inst.is_published = True
            inst.save(update_fields=['is_published', 'status'])
            return inst

        # Not publishing — save as draft
        validated_data['status'] = Chapter.STATUS_DRAFT
        validated_data.pop('is_published', None)
        return super().update(instance, validated_data)
