from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Notification, DeviceToken
from .serializers import NotificationSerializer, DeviceTokenSerializer


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .models import DeviceToken, PushNotificationLog
from .services import notify_all, notify_user, notify_by_genre
from django.utils import timezone
 
 
class RegisterTokenView(APIView):
    # \"\"\"POST /api/notifications/register-token/\"\"\"
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
 
    def post(self, request):
        token        = request.data.get('token', '').strip()
        platform     = request.data.get('platform', 'Android')
        device_model = request.data.get('device_model', '')
        app_version  = request.data.get('app_version', '')
 
        if not token:
            return Response({'detail': 'Token required'},
                status=status.HTTP_400_BAD_REQUEST)
 
        obj, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                'user':         request.user if request.user.is_authenticated else None,
                'platform':     platform,
                'device_model': device_model,
                'app_version':  app_version,
                'is_active':    True,
            }
        )
        return Response({'message': 'Token registered', 'created': created})
 
 
class AdminSendNotificationView(APIView):
    # \"\"\"
    # POST /api/notifications/admin/send/
    # Admin-only endpoint to send notifications from the API or admin panel.
    # \"\"\"
    permission_classes = [permissions.IsAdminUser]
 
    def post(self, request):
        title     = request.data.get('title', '')
        body      = request.data.get('body', '')
        audience  = request.data.get('audience', 'all')
        data      = request.data.get('data', {})
        image_url = request.data.get('image_url', '')
        user_id   = request.data.get('user_id')
        genre     = request.data.get('genre_slug', '')
 
        if not title or not body:
            return Response({'detail': 'title and body required'},
                status=status.HTTP_400_BAD_REQUEST)
 
        log = PushNotificationLog.objects.create(
            title=title, body=body, data=data,
            image_url=image_url, audience=audience,
            genre_slug=genre,
            created_by=request.user, status='pending')
 
        result = {'success': 0, 'failed': 0}
 
        try:
            if audience == 'all':
                result = notify_all(title, body, data, image_url)
            elif audience == 'user' and user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(pk=user_id)
                notify_user(user, title, body, data, image_url)
                result = {'success': 1, 'failed': 0}
            elif audience == 'genre' and genre:
                notify_by_genre(genre, title, body, data)
 
            log.status      = 'sent'
            log.sent_count  = result.get('success', 0)
            log.failed_count= result.get('failed', 0)
            log.sent_at     = timezone.now()
        except Exception as e:
            log.status = 'failed'
            result = {'error': str(e)}
        finally:
            log.save()
 
        return Response({**result, 'log_id': log.id})

class NotificationListView(generics.ListAPIView):
    serializer_class   = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class UnreadNotificationCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread_count': count})


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'detail': 'Marked as read.'})


class MarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'detail': 'All notifications marked as read.'})


class RegisterDeviceTokenView(generics.CreateAPIView):
    serializer_class   = DeviceTokenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        token    = serializer.validated_data['token']
        platform = serializer.validated_data['platform']
        DeviceToken.objects.update_or_create(
            token=token,
            defaults={'user': self.request.user, 'platform': platform, 'is_active': True}
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'detail': 'Device registered.'}, status=201)


class DeregisterDeviceTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'detail': 'token required.'}, status=400)
        DeviceToken.objects.filter(user=request.user, token=token).update(is_active=False)
        return Response({'detail': 'Device deregistered.'}, status=204)
