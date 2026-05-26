# # serializers.py
# from rest_framework import serializers
# from .models import Tip, TIP_AMOUNTS
# from apps.users.serializers import PublicUserSerializer


# class TipSerializer(serializers.ModelSerializer):
#     sender    = PublicUserSerializer(read_only=True)
#     recipient = PublicUserSerializer(read_only=True)

#     class Meta:
#         model  = Tip
#         fields = ['id', 'sender', 'recipient', 'story', 'chapter',
#                   'coins_amount', 'message', 'created_at']


# class SendTipSerializer(serializers.Serializer):
#     coins_amount = serializers.IntegerField()
#     message      = serializers.CharField(max_length=255, required=False, allow_blank=True)
#     chapter_id   = serializers.IntegerField(required=False)

#     def validate_coins_amount(self, value):
#         if value not in TIP_AMOUNTS:
#             raise serializers.ValidationError(f'Tip must be one of: {TIP_AMOUNTS}')
#         return value


# serializers.py
from rest_framework import serializers
from .models import Tip, TIP_AMOUNTS
from apps.users.serializers import PublicUserSerializer


class TipSerializer(serializers.ModelSerializer):
    sender    = PublicUserSerializer(read_only=True)
    recipient = PublicUserSerializer(read_only=True)

    class Meta:
        model  = Tip
        fields = ['id', 'sender', 'recipient', 'story', 'chapter',
                  'coins_amount', 'message', 'created_at']


class SendTipSerializer(serializers.Serializer):
    # Accept both int and string representations of the amount
    coins_amount = serializers.IntegerField(
        error_messages={'invalid': 'A valid integer is required.'}
    )
    message    = serializers.CharField(max_length=255, required=False, allow_blank=True)
    chapter_id = serializers.IntegerField(required=False)

    def to_internal_value(self, data):
        # Coerce coins_amount to int if it arrives as a string
        if 'coins_amount' in data:
            try:
                data = dict(data)
                data['coins_amount'] = int(data['coins_amount'])
            except (ValueError, TypeError):
                pass
        return super().to_internal_value(data)

    def validate_coins_amount(self, value):
        if value not in TIP_AMOUNTS:
            raise serializers.ValidationError(
                f'Invalid amount. Allowed values: {TIP_AMOUNTS}'
            )
        return value