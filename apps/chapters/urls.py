from django.urls import path
from . import views

urlpatterns = [
    path('<slug:story_slug>/chapters/',                                views.ChapterListCreateView.as_view()),
    path('<slug:story_slug>/chapters/download/',                       views.DownloadStoryView.as_view()),
    path('<slug:story_slug>/chapters/<int:chapter_number>/',           views.ChapterDetailView.as_view()),
    path('<slug:story_slug>/chapters/<int:chapter_number>/unlock/',    views.UnlockChapterView.as_view()),
    path('<slug:story_slug>/chapters/<int:chapter_number>/publish/',   views.PublishChapterView.as_view()),
    path('<slug:story_slug>/chapters/<int:chapter_number>/submit-review/', views.SubmitChapterEditForReviewView.as_view()),
]