from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.chapters.models import Chapter
from .models import EditorAssignment, AuthorEditorLink

User = get_user_model()


class EditorMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'role']


class EditorAssignmentSerializer(serializers.ModelSerializer):
    editor_detail     = EditorMinimalSerializer(source='editor',     read_only=True)
    supervisor_detail = EditorMinimalSerializer(source='supervisor', read_only=True)

    class Meta:
        model  = EditorAssignment
        fields = ['id', 'editor', 'supervisor', 'editor_detail', 'supervisor_detail',
                  'assigned_at', 'notes']

    def validate_editor(self, value):
        if value.role != 'se':
            raise serializers.ValidationError('Editor must have role se.')
        return value

    def validate_supervisor(self, value):
        if value and value.role != 'ce':
            raise serializers.ValidationError('Supervisor must be a CE.')
        return value


class AuthorEditorLinkSerializer(serializers.ModelSerializer):
    author_detail = EditorMinimalSerializer(source='author',      read_only=True)
    se_detail     = EditorMinimalSerializer(source='assigned_se', read_only=True)
    ce            = serializers.SerializerMethodField()

    class Meta:
        model  = AuthorEditorLink
        fields = ['id', 'author', 'assigned_se', 'author_detail', 'se_detail',
                  'ce', 'link_method', 'assigned_at', 'notes']

    def get_ce(self, obj):
        ce = obj.get_ce()
        return EditorMinimalSerializer(ce).data if ce else None


class ChapterReviewListSerializer(serializers.ModelSerializer):
    chapter_title    = serializers.CharField(source='title', read_only=True)
    story_title      = serializers.CharField(source='story.title', read_only=True)
    author_name      = serializers.CharField(source='story.author.username', read_only=True)
    assigned_se_name = serializers.SerializerMethodField()
    submitted_at     = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model  = Chapter
        fields = [
            'id', 'story', 'chapter_number', 'title', 'chapter_title',
            'story_title', 'author_name', 'status', 'is_published',
            'submitted_at', 'updated_at', 'assigned_se_name',
        ]

    def get_assigned_se_name(self, obj):
        link = getattr(obj.story.author, 'editor_link', None)
        if link and link.assigned_se:
            return link.assigned_se.username
        return None


class ChapterReviewDetailSerializer(serializers.ModelSerializer):
    story_title      = serializers.CharField(source='story.title', read_only=True)
    author_name      = serializers.CharField(source='story.author.username', read_only=True)
    chapter_content  = serializers.CharField(source='content', read_only=True)
    assigned_se_name = serializers.SerializerMethodField()

    class Meta:
        model  = Chapter
        fields = [
            'id', 'story', 'chapter_number', 'title', 'chapter_content',
            'story_title', 'author_name', 'status', 'is_published',
            'word_count', 'assigned_se_name',
            'se_note', 'reviewed_by_se', 'reviewed_at', 'created_at', 'updated_at',
        ]

    def get_assigned_se_name(self, obj):
        link = getattr(obj.story.author, 'editor_link', None)
        if link and link.assigned_se:
            return link.assigned_se.username
        return None
