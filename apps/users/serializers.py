from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from dj_rest_auth.registration.serializers import RegisterSerializer as BaseRegisterSerializer
from .models import User, AuthorProfile, Follow, FCMDevice, UserPreferences


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ── Custom JWT: embed role in token payload ───────────────────────────────────

class NoveluXTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds `role` and `username` to the JWT payload so the web layer
    can gate dashboard access without an extra /me API call."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role']     = user.role
        token['username'] = user.username
        return token


class NoveluXTokenObtainPairView(TokenObtainPairView):
    serializer_class = NoveluXTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            device_id = request.data.get('device_id', '').strip()
            platform  = request.data.get('platform', '').strip().lower()
            if device_id:
                try:
                    from .models import UserDevice
                    from django.contrib.auth import get_user_model
                    _User = get_user_model()
                    email = request.data.get('email', '')
                    user  = _User.objects.filter(email=email).first()
                    if user:
                        UserDevice.objects.update_or_create(
                            user=user, device_id=device_id,
                            defaults={'platform': platform},
                        )
                except Exception:
                    pass
        return response


class RegisterSerializer(BaseRegisterSerializer):
    username    = serializers.CharField(required=True)
    role        = serializers.ChoiceField(choices=User.ROLE_CHOICES, default=User.ROLE_READER)
    editor_code = serializers.CharField(
        required=False, allow_blank=True, default='',
        help_text=(
            "Optional. Authors enter their editor's invite code to link automatically."
        ),
    )

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data['role']        = self.validated_data.get('role', User.ROLE_READER)
        data['editor_code'] = self.validated_data.get('editor_code', '').strip().upper()
        return data

    def validate_editor_code(self, value):
        value = value.strip().upper()
        if not value:
            return value
        role = self.initial_data.get('role', 'reader')
        if role != 'author':
            return value   # non-authors: ignore code
        if not User.objects.filter(editor_code=value, role='se').exists():
            raise serializers.ValidationError(
                'Invalid editor code. Double-check the code with your editor.'
            )
        return value

    def validate(self, data):
        data = super().validate(data)
        return data

    def save(self, request):
        from .models import BlacklistedIP
        ip = _get_client_ip(request)
        if ip and BlacklistedIP.objects.filter(ip_address=ip).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Registration is not available from this network.')

        user = super().save(request)
        user.role = self.cleaned_data.get('role', User.ROLE_READER)
        user.registration_ip = ip
        user.save()

        # Track device ID if provided
        device_id = request.data.get('device_id', '').strip()
        platform  = request.data.get('platform', '').strip().lower()
        if device_id:
            from .models import UserDevice
            UserDevice.objects.update_or_create(
                user=user, device_id=device_id,
                defaults={'platform': platform},
            )

        if user.role == User.ROLE_AUTHOR:
            AuthorProfile.objects.get_or_create(user=user)
            from apps.editorial.models import AuthorEditorLink
            code = self.cleaned_data.get('editor_code', '')
            if code:
                AuthorEditorLink.link_by_code(user, code)
            else:
                AuthorEditorLink.auto_assign(user)

        return user

class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = ['preferred_genres', 'gender', 'updated_at']
        read_only_fields = ['updated_at']

    def validate_preferred_genres(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Must be a list of genre slugs.')
        return value

class AuthorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AuthorProfile
        fields = ['pen_name', 'total_earnings', 'pending_payout', 'completion_bonus',
                  'contract_type', 'is_verified', 'joined_as_author']
        read_only_fields = ['total_earnings', 'pending_payout', 'completion_bonus',
                            'is_verified', 'joined_as_author']


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FCMDevice
        fields = ['token', 'platform', 'device_model', 'app_version']
        # read_only_fields = ['total_earnings', 'pending_payout', 'is_verified', 'joined_as_author']


class UserSerializer(serializers.ModelSerializer):
    author_profile    = AuthorProfileSerializer(read_only=True)
    followers_count   = serializers.SerializerMethodField()
    following_count   = serializers.SerializerMethodField()
    display_name      = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'author_code', 'username', 'display_name', 'first_name', 'last_name', 'email', 'role',
            'avatar', 'bio', 'coin_balance', 'is_vip', 'vip_expires',
            'ad_free_expires', 'audiobook_expires',
            'reading_xp', 'reading_level', 'total_chapters_read',
            'preferred_genres', 'preferred_language', 'night_mode', 'font_size',
            'author_profile', 'followers_count', 'following_count', 'created_at',
        ]
        read_only_fields = ['coin_balance', 'is_vip', 'vip_expires',
                            'ad_free_expires', 'audiobook_expires',
                            'reading_xp', 'reading_level', 'total_chapters_read', 'created_at']

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_display_name(self, obj):
        try:
            pen = obj.author_profile.pen_name
            if pen and pen.strip():
                return pen.strip()
        except AttributeError:
            pass
        return obj.username


class PublicUserSerializer(serializers.ModelSerializer):
    """Minimal public profile."""
    author_profile  = AuthorProfileSerializer(read_only=True)
    followers_count = serializers.SerializerMethodField()
    display_name    = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'author_code', 'username', 'display_name', 'avatar', 'bio', 'role',
                  'reading_level', 'author_profile', 'followers_count']

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_display_name(self, obj):
        """Returns pen name if set, otherwise falls back to username."""
        try:
            pen = obj.author_profile.pen_name
            if pen and pen.strip():
                return pen.strip()
        except AttributeError:
            pass
        return obj.username


class UpdatePreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['preferred_genres', 'preferred_language', 'night_mode', 'font_size', 'bio', 'avatar']


class FollowSerializer(serializers.ModelSerializer):
    follower  = PublicUserSerializer(read_only=True)
    following = PublicUserSerializer(read_only=True)

    class Meta:
        model  = Follow
        fields = ['id', 'follower', 'following', 'created_at']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    pen_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'avatar', 'pen_name']

    def update(self, instance, validated_data):
        pen_name = validated_data.pop('pen_name', None)
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if pen_name is not None:
            profile, _ = AuthorProfile.objects.get_or_create(user=instance)
            profile.pen_name = pen_name
            profile.save(update_fields=['pen_name'])

        if first_name is not None and last_name is not None:
            instance.first_name = first_name
            instance.last_name = last_name
            instance.save(update_fields=['first_name', 'last_name'])

        return instance