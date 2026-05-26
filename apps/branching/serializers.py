# serializers.py
from rest_framework import serializers
from .models import BranchPoint, BranchChoice, BranchVote


class BranchChoiceSerializer(serializers.ModelSerializer):
    vote_percentage = serializers.ReadOnlyField()

    class Meta:
        model  = BranchChoice
        fields = ['id', 'label', 'description', 'votes_count', 'vote_percentage', 'is_winner']


class BranchPointSerializer(serializers.ModelSerializer):
    choices     = BranchChoiceSerializer(many=True, read_only=True)
    total_votes = serializers.ReadOnlyField()
    user_vote   = serializers.SerializerMethodField()

    class Meta:
        model  = BranchPoint
        fields = ['id', 'chapter', 'prompt', 'position', 'voting_open',
                  'voting_ends', 'choices', 'total_votes', 'user_vote', 'created_at']

    def get_user_vote(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            vote = BranchVote.objects.filter(user=request.user, branch_point=obj).first()
            return vote.choice_id if vote else None
        return None


class CreateBranchPointSerializer(serializers.ModelSerializer):
    choices = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )

    class Meta:
        model  = BranchPoint
        fields = ['chapter', 'prompt', 'position', 'voting_ends', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices')
        branch_point = BranchPoint.objects.create(**validated_data)
        for c in choices_data:
            BranchChoice.objects.create(
                branch_point=branch_point,
                label=c.get('label', ''),
                description=c.get('description', ''),
            )
        return branch_point


class CastVoteSerializer(serializers.Serializer):
    choice_id = serializers.IntegerField()
