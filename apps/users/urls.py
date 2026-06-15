from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from .serializers import NoveluXTokenObtainPairView
from . import views

urlpatterns = [
    path('me/',                        views.MeView.as_view()),
    path('token/',                     NoveluXTokenObtainPairView.as_view()),   # role in payload
    path('token/refresh/',             TokenRefreshView.as_view()),
    path('token/blacklist/',           TokenBlacklistView.as_view()),
    path('social/',                    views.SocialLoginView.as_view()),
    path('become-author/',             views.BecomeAuthorView.as_view()),
    path('profile/<str:username>/',    views.PublicProfileView.as_view()),
    path('follow/<str:username>/',     views.FollowUserView.as_view()),
    path('<str:username>/followers/',  views.FollowersListView.as_view()),
    path('<str:username>/following/',  views.FollowingListView.as_view()),
    path('save-fcm-token/',            views.SaveFCMToken.as_view(), name='save-fcm-token'),
    path('google/',                    views.GoogleSignInView.as_view(),  name='google-signin'),
    path('preferences/',               views.UserPreferencesView.as_view(), name='user-preferences'),
]
