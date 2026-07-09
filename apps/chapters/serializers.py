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

        if is_publish:
            validated_data['status'] = Chapter.STATUS_DRAFT
            instance = super().create(validated_data)

            story = instance.story
            story.refresh_from_db(fields=['contract_status'])

            if story.contract_status == 'signed':
                # Contracted author → publish_held_chapters_for_author already ran
                # in _check_editorial_trigger; nothing more needed here.
                pass
            else:
                # Non-contracted author → send to SE incoming queue
                instance.status = Chapter.STATUS_PENDING_REVIEW
                instance.save(update_fields=['status'])

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
            validated_data.pop('status', None)
            inst = super().update(instance, validated_data)

            story = inst.story
            story.refresh_from_db(fields=['contract_status'])

            if story.contract_status == 'signed':
                # Contracted author → publish immediately
                inst.status      = Chapter.STATUS_PUBLISHED
                inst.is_published = True
                inst.save(update_fields=['status', 'is_published'])
            else:
                # Non-contracted author → send to SE incoming queue
                inst.status = Chapter.STATUS_PENDING_REVIEW
                inst.save(update_fields=['status'])

            return inst

        # Plain save (no publish intent) — keep as draft
        validated_data['status'] = Chapter.STATUS_DRAFT
        validated_data.pop('is_published', None)
        return super().update(instance, validated_data)
