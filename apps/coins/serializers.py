from rest_framework import serializers

from apps.stories.models import Story
from .models import CoinPackage, ReadingHistory, SubscriptionPlan, Purchase, Subscription, AuthorPayout
from apps.users.models import CoinTransaction


class CoinPackageSerializer(serializers.ModelSerializer):
    total_coins = serializers.ReadOnlyField()

    class Meta:
        model  = CoinPackage
        fields = ['id', 'package_id', 'label', 'coins', 'bonus_coins', 'total_coins', 'price_usd']


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SubscriptionPlan
        fields = ['id', 'plan_id', 'label', 'price_usd', 'coins_per_month',
                  'discount_pct', 'duration_days', 'badge', 'is_primary', 'sub_title']


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Purchase
        fields = ['id', 'purchase_type', 'coins_granted', 'amount_paid_usd',
                  'status', 'created_at', 'completed_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model  = Subscription
        fields = ['id', 'plan', 'started_at', 'expires_at', 'is_active', 'auto_renew']


class CoinTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CoinTransaction
        fields = ['id', 'amount', 'transaction_type', 'reason', 'balance_after', 'created_at']


class AuthorPayoutRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AuthorPayout
        fields = ['id', 'amount_usd', 'coins_total', 'payout_method',
                  'status', 'requested_at', 'processed_at']
        read_only_fields = ['status', 'requested_at', 'processed_at']


class CreateCheckoutSessionSerializer(serializers.Serializer):
    package_id    = serializers.CharField(required=False)
    plan_id       = serializers.CharField(required=False)
    purchase_type = serializers.ChoiceField(choices=['coin_pack', 'subscription'])

    def validate(self, data):
        if data['purchase_type'] == 'coin_pack' and not data.get('package_id'):
            raise serializers.ValidationError('package_id required for coin_pack purchase.')
        if data['purchase_type'] == 'subscription' and not data.get('plan_id'):
            raise serializers.ValidationError('plan_id required for subscription purchase.')
        return data

# //READING_HISTORY_SERIALIZER = """
class StoryMiniSerializer(serializers.ModelSerializer):
    # \"\"\"Minimal story info for history list.\"\"\"
    class Meta:
        model  = Story
        fields = ['slug', 'title', 'cover_image', 'status',
                  'total_chapters', 'genre']
 
class ReadingHistorySerializer(serializers.ModelSerializer):
    story = StoryMiniSerializer(read_only=True)
 
    class Meta:
        model  = ReadingHistory
        fields = ['id', 'story', 'chapter_number', 'chapter_title', 'read_at']
        read_only_fields = ['id', 'read_at']