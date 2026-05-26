from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerUIView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    #home page
    path('', include('novelux_web.urls')),

    #admin dashboard
    path('admin/', admin.site.urls),

    # API schema & docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/',   SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Auth
    path('api/auth/',         include('apps.users.urls')),
    path('api/auth/social/',  include('allauth.socialaccount.urls')),
    path('api/auth/dj/',      include('dj_rest_auth.urls')),
    path('api/auth/dj/registration/', include('dj_rest_auth.registration.urls')),

    # Core features
    path('api/stories/',      include('apps.stories.urls')),
    path('api/chapters/',     include('apps.chapters.urls')),
    path('api/coins/',        include('apps.coins.urls')),
    path('api/audio/',        include('apps.audio.urls')),
    path('api/comments/',     include('apps.comments.urls')),
    path('api/tips/',         include('apps.tips.urls')),
    path('api/branching/',    include('apps.branching.urls')),
    path('api/notifications/',include('apps.notifications.urls')),
    path('api/stories/reviews/', include('apps.reviews.urls')),
    path('api/editorial/',    include('apps.editorial.urls')),  # AE/SE/CE editorial workflow
    
     # Reading sessions & schedule (add to coins urls, NOT a separate file)
    path('api/reading/', include('apps.coins.reading_urls')),

    path('api/users/', include('apps.users.profile_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
