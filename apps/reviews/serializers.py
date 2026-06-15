from rest_framework import serializers
from .models import StoryReview, Report, ReportMissingStory


class ReviewUserSerializer(serializers.Serializer):
    id       = serializers.IntegerField()
    username = serializers.CharField()
    avatar   = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            url = obj.avatar.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return ''


class StoryReviewSerializer(serializers.ModelSerializer):
    user        = ReviewUserSerializer(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    is_liked    = serializers.SerializerMethodField()

    class Meta:
        model  = StoryReview
        fields = ['id', 'user', 'rating', 'content',
                  'likes_count', 'is_liked', 'created_at']

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(pk=request.user.pk).exists()
        return False


class CreateReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StoryReview
        fields = ['rating', 'content']

    def validate_rating(self, value):
        allowed = ['recommend', 'average', 'not_good']
        if value not in allowed:
            raise serializers.ValidationError(
                f'Rating must be one of: {allowed}')
        return value


class ReportSerializer(serializers.Serializer):
    class Meta:
        model  = Report
        fields = ['id','user', 'reason', 'phone', 'image']


class ReportMissingStorySerializer(serializers.Serializer):
    class Meta:
        model  = ReportMissingStory
        fields = ['id','user', 'reason', 'phone', 'image']        