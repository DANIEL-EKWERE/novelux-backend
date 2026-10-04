# serializers.py
from rest_framework import serializers
from .models import Tip, GIFTS, FLOWER, LABEL_BY_COINS
from apps.users.serializers import PublicUserSerializer


class TipSerializer(serializers.ModelSerializer):
    sender    = PublicUserSerializer(read_only=True)
    recipient = PublicUserSerializer(read_only=True)

    class Meta:
        model  = Tip
        fields = ['id', 'sender', 'recipient', 'story', 'chapter',
                  'coins_amount', 'gift_label', 'status', 'amount_usd', 'message', 'created_at']


class SendTipSerializer(serializers.Serializer):
    # Accept both int and string representations of the amount
    coins_amount   = serializers.IntegerField(
        error_messages={'invalid': 'A valid integer is required.'}
    )
    gift_label     = serializers.CharField(max_length=32, required=False, allow_blank=True)
    message        = serializers.CharField(max_length=255, required=False, allow_blank=True)
    chapter_id     = serializers.IntegerField(required=False)
    chapter_number = serializers.IntegerField(required=False)

    def to_internal_value(self, data):
        # Coerce coins_amount to int if it arrives as a string
        if 'coins_amount' in data:
            try:
                data = dict(data)
                data['coins_amount'] = int(data['coins_amount'])
            except (ValueError, TypeError):
                pass
        return super().to_internal_value(data)

    def validate(self, attrs):
        coins = attrs['coins_amount']
        label = attrs.get('gift_label') or LABEL_BY_COINS.get(coins)
        if label not in GIFTS:
            raise serializers.ValidationError(
                {'coins_amount': f'Invalid amount. Allowed values: {sorted(LABEL_BY_COINS)}'}
            )
        # The price comes from the catalogue, never the client.
        if GIFTS[label].coins != coins:
            raise serializers.ValidationError({'gift_label': f'{label} costs {GIFTS[label].coins} coins.'})
        attrs['gift_label'] = label
        return attrs


class GiftIntentSerializer(serializers.Serializer):
    gift_label     = serializers.ChoiceField(choices=[l for l in GIFTS if l != FLOWER])
    message        = serializers.CharField(max_length=255, required=False, allow_blank=True)
    chapter_id     = serializers.IntegerField(required=False)
    chapter_number = serializers.IntegerField(required=False)
