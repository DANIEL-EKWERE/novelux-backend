from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Follow, AuthorProfile, FCMDevice
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    ProfileUpdateSerializer, UserSerializer, PublicUserSerializer,
    UpdatePreferencesSerializer, FollowSerializer, FCMDeviceSerializer
)
from .models import UserPreferences
from .serializers import UserPreferencesSerializer
 
from firebase_admin import messaging

User = get_user_model()




 

 
GOOGLE_CLIENT_IDS = [
    '302060725266-si3i60jiots71onc2o075ta6c63gnkfu.apps.googleusercontent.com',
    '302060725266-8lm05k7jgm0dlbl1p2ht5hkfifdg1cq8.apps.googleusercontent.com',   # optional web
    '302060725266-8r9c6525a9c810f75geigek68a5339u6.apps.googleusercontent.com' #ios
]
 
 
class GoogleSignInView(APIView):
    # \"\"\"
    # POST /api/auth/google/
    # Body: { id_token, email, display_name?, photo_url? }
    # Returns the same access/refresh tokens as a normal login.
    # \"\"\"
    permission_classes = []   # public
 
    def post(self, request):
        id_token     = request.data.get('id_token', '').strip()
        access_token = request.data.get('access_token', '').strip()
        email        = request.data.get('email', '').strip().lower()
        display_name = request.data.get('display_name', '') or request.data.get('name', '')
        photo_url    = request.data.get('photo_url', '')

        if not id_token and not access_token:
            return Response({'detail': 'id_token or access_token is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        # ── Verify with Google ───────────────────────────────────────────────
        if id_token:
            # Preferred path: verify the signed JWT id_token
            try:
                idinfo = google_id_token.verify_oauth2_token(
                    id_token,
                    google_requests.Request(),
                    audience=None,
                )
            except ValueError as e:
                return Response({'detail': f'Invalid Google token: {e}'},
                                status=status.HTTP_401_UNAUTHORIZED)
        else:
            # Fallback path: verify via userinfo endpoint using the access_token
            # (used by initTokenClient flow which doesn't return an id_token)
            import requests as _req
            try:
                r = _req.get(
                    'https://www.googleapis.com/oauth2/v3/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=5,
                )
                if r.status_code != 200:
                    return Response({'detail': 'Invalid Google access token'},
                                    status=status.HTTP_401_UNAUTHORIZED)
                idinfo = r.json()
            except Exception as e:
                return Response({'detail': f'Google verification failed: {e}'},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        google_email = (idinfo.get('email') or email).lower()
        google_name  = idinfo.get('name') or display_name
        google_photo = idinfo.get('picture') or photo_url

        if not google_email:
            return Response({'detail': 'Could not determine email from Google account'},
                            status=status.HTTP_400_BAD_REQUEST)
 
        # ── Get or create user ───────────────────────────────────────────────
        user, created = User.objects.get_or_create(
            email=google_email,
            defaults={
                'username': _make_username(google_name, google_email),
                'first_name': google_name.split()[0] if google_name else '',
                'last_name':  ' '.join(google_name.split()[1:]) if google_name else '',
            }
        )
        code = 200
        if created:
            code = 201
            user.set_unusable_password()   # Google users have no password
            user.save()
 
            # Store photo URL if your model supports it
            if hasattr(user, 'avatar') and google_photo:
                user.avatar = google_photo
                user.save(update_fields=['avatar'])
 
            # Fire welcome notification
            try:
                from apps.notifications.services import on_user_signup
                on_user_signup(user)
            except Exception:
                pass
 
        # ── Issue JWT tokens ─────────────────────────────────────────────────
        refresh = RefreshToken.for_user(user)
        return Response({
            'access':    str(refresh.access_token),
            'refresh':   str(refresh),
            'username':  user.username,
            'email':     user.email,
            'is_new':    created,
            'code':      code
        })
 
 
def _make_username(display_name: str, email: str) -> str:
    # \"\"\"Generate a unique username from display name or email.\"\"\"
    base = (display_name or email.split('@')[0])
    base = base.lower().replace(' ', '_')[:20]
    # Ensure uniqueness
    username = base
    i = 1
    while User.objects.filter(username=username).exists():
        username = f'{base}_{i}'
        i += 1
    return username



class MeView(generics.RetrieveUpdateAPIView):
    """Get or update the authenticated user's profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UpdatePreferencesSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user


class PublicProfileView(generics.RetrieveAPIView):
    serializer_class   = PublicUserSerializer
    queryset           = User.objects.all()
    lookup_field       = 'username'


class FollowUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, username):
        target = get_object_or_404(User, username=username)
        if target == request.user:
            return Response({'detail': 'You cannot follow yourself.'}, status=400)
        follow, created = Follow.objects.get_or_create(
            follower=request.user, following=target
        )
        if not created:
            return Response({'detail': 'Already following.'}, status=400)
        return Response({'detail': f'Now following {username}.'}, status=201)

    def delete(self, request, username):
        target = get_object_or_404(User, username=username)
        Follow.objects.filter(follower=request.user, following=target).delete()
        return Response({'detail': f'Unfollowed {username}.'}, status=204)


class FollowersListView(generics.ListAPIView):
    serializer_class = PublicUserSerializer

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs['username'])
        return User.objects.filter(following__following=user)


class FollowingListView(generics.ListAPIView):
    serializer_class = PublicUserSerializer

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs['username'])
        return User.objects.filter(followers__follower=user)
    
# class SaveFCMToken(APIView):
#     permission_classes = [permissions.IsAuthenticated]
#     serializer_class = FCMDeviceSerializer

#     def post(self, request):
#         token = request.data.get('token')
#         token = request.data.get('platform')

#         if not token:
#             return Response({"error": "no token provided"}, status=400)
        
#         FCMDevice.object.update_or_create(
#             user=request.user,
#             defaults={'token': token}
#         )
#         return Response({"mesasge sent": "Token saved."}, status=200)    

class SaveFCMToken(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # This helps with documentation like Swagger
    serializer_class = FCMDeviceSerializer

    def post(self, request):
        # 1. Pass the data to the serializer
        serializer = self.serializer_class(data=request.data)

        # 2. Check if the token/platform are valid based on your serializer rules
        if serializer.is_valid():
            token = serializer.validated_data['token']
            platform = serializer.validated_data.get('platform', 'android')
            appVersion = serializer.validated_data.get('app_version', '1.0.0')
            deviceModel = serializer.validated_data.get('device_model', 'TECNO')

            # 3. Use update_or_create to link it to the current user
            device, created = FCMDevice.objects.update_or_create(
                token=token,
                defaults={
                    'user' : request.user if request.user.is_authenticated else None,
                    'platform': platform,
                    'app_version': appVersion,
                    'device_model': deviceModel,
                }
            )

            return Response({
                "message": "Token saved successfully",
                "created": created
            }, status=status.HTTP_200_OK)

        # 4. If data is bad (e.g. missing token), return the exact errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserPreferencesView(APIView):
   
    permission_classes = [permissions.IsAuthenticated]
 
    def get(self, request):
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        return Response(UserPreferencesSerializer(prefs).data)
 
    def post(self, request):
        prefs, created = UserPreferences.objects.get_or_create(user=request.user)
        s = UserPreferencesSerializer(prefs, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data,
            status=201 if created else 200)

class BecomeAuthorView(APIView):
    """
    POST /api/users/become-author/
    Body (optional): { "editor_code": "AX3K9PLM" }

    Upgrades a reader account to author and optionally links them to an AE.
    If no code is provided, auto-assigns to the AE with lowest author load.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.is_author:
            return Response({'detail': 'Already an author.'}, status=400)

        user.role = User.ROLE_AUTHOR
        user.save()
        AuthorProfile.objects.get_or_create(user=user)

        # Link to Senior Editor
        from apps.editorial.models import AuthorEditorLink
        code = request.data.get('editor_code', '').strip().upper()
        link_result = {}
        if code:
            link, err = AuthorEditorLink.link_by_code(user, code)
            if err:
                # Don't block the upgrade — just report the code issue
                link_result = {'editor_warning': err}
            else:
                se = link.assigned_se
                link_result = {'editor_linked': se.username if se else ''}
        else:
            link, _ = AuthorEditorLink.auto_assign(user)
            if link and link.assigned_se:
                link_result = {'editor_auto_assigned': link.assigned_se.username}

        return Response({'detail': 'You are now an author!', **link_result}, status=200)


class SocialLoginView(APIView):
    """
    Exchange a Google/Facebook access token for JWT tokens.
    POST { provider: 'google'|'facebook', access_token: '...' }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
        from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
        from dj_rest_auth.registration.views import SocialLoginView as BaseSocialLoginView

        provider = request.data.get('provider')
        if provider == 'google':
            view = BaseSocialLoginView.as_view(adapter_class=GoogleOAuth2Adapter)
        elif provider == 'facebook':
            view = BaseSocialLoginView.as_view(adapter_class=FacebookOAuth2Adapter)
        else:
            return Response({'detail': 'Invalid provider.'}, status=400)
        return view(request._request)


def send_notification_to_followers(author, title, body):
    followers = User.objects.filter(following__following=author)
    tokens = []
    for follower in followers:
        profile = AuthorProfile.objects.filter(user=follower).first()
        if profile and profile.fcm_token:
            tokens.append(profile.fcm_token)

    if not tokens:
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        tokens=tokens,
    )
    response = messaging.send_multicast(message)
    print(f'Sent {response.success_count} notifications, {response.failure_count} failures.')


def send_data_message(token, title, body, image_url=None):
    message = messaging.Message(
        data={'title': title, 'body': body},
        token=token,
        notification=messaging.Notification(title=title, body=body) if image_url else None,
        android=messaging.AndroidConfig(
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                image=image_url
            )
        ) if image_url else None
    )
    response = messaging.send(message)
    print(f'Sent data message with response: {response}')


from rest_framework import parsers

class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/users/me/  — fetch full profile
    PATCH /api/users/me/ — update first_name, last_name, bio, avatar, pen_name
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ProfileUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user