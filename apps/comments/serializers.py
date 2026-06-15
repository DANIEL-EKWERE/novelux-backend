# serializers.py
from rest_framework import serializers
from .models import Comment, CommentLike
from apps.users.serializers import PublicUserSerializer


class CommentSerializer(serializers.ModelSerializer):
    user        = PublicUserSerializer(read_only=True)
    reply_count = serializers.SerializerMethodField()
    is_liked    = serializers.SerializerMethodField()
    replies     = serializers.SerializerMethodField()

    class Meta:
        model  = Comment
        fields = [
            'id', 'user', 'content', 'paragraph_index',
            'likes_count', 'is_pinned', 'is_author_reply',
            'reply_count', 'is_liked', 'replies',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['likes_count', 'is_pinned', 'is_author_reply']

    def get_reply_count(self, obj):
        return obj.replies.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CommentLike.objects.filter(user=request.user, comment=obj).exists()
        return False

    def get_replies(self, obj):
        if obj.parent is None:
            qs = obj.replies.select_related('user')[:5]
            return CommentSerializer(qs, many=True, context=self.context).data
        return []


class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Comment
        fields = ['content', 'paragraph_index', 'parent']
