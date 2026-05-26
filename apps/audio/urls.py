from django.urls import path
from . import views

urlpatterns = [
    path('<slug:story_slug>/chapters/<int:chapter_number>/audio/',
         views.ChapterAudioView.as_view()),
    path('progress/<int:audio_chapter_id>/',
         views.UpdateAudioProgressView.as_view()),
]
