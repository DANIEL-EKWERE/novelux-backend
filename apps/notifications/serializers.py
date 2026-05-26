# serializers.py
from rest_framework import serializers
from .models import Notification, DeviceToken


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ['id', 'notification_type', 'title', 'message',
                  'data', 'is_read', 'created_at']


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DeviceToken
        fields = ['id', 'token', 'platform', 'created_at']
        read_only_fields = ['created_at']
