from django.urls import path
from . import views

urlpatterns = [
    # Editorial: held author earnings from chapter unlocks (SE / CE / admin).
    # Declared before the <slug:story_slug> routes so 'earnings' can't be read
    # as a story slug.
    path('earnings/held/',              views.HeldEarningsView.as_view()),
    path('earnings/<int:pk>/release/',  views.ReleaseEarningView.as_view(),
         {'action': 'release'}),
    path('earnings/<int:pk>/reject/',   views.ReleaseEarningView.as_view(),
         {'action': 'reject'}),

    path('<slug:story_slug>/chapters/',                                views.ChapterListCreateView.as_view()),
    path('<slug:story_slug>/chapters/download/',                       views.DownloadStoryView.as_view()),
    path('<slug:story_slug>/chapters/<int:chapter_number>/',           views.ChapterDetailView.as_view()),
    path('<slug:story_slug>/chapters/<int:chapter_number>/unlock/',    views.UnlockChapterView.as_view()),
    path('<slug:story_slug>/chapters/<int:chapter_number>/ad-access/', views.AdAccessChapterView.as_view()),
    path('<slug:story_slug>/chapters/<int:chapter_number>/publish/',   views.PublishChapterView.as_view()),
    path('<slug:story_slug>/chapters/<int:chapter_number>/submit-review/', views.SubmitChapterEditForReviewView.as_view()),
]