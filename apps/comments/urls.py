from django.urls import path
from . import views

urlpatterns = [
    path('<slug:story_slug>/chapters/<int:chapter_number>/comments/',
         views.ChapterCommentListCreateView.as_view()),
    path('comment/<int:pk>/',       views.CommentDetailView.as_view()),
    path('comment/<int:pk>/like/',  views.LikeCommentView.as_view()),
    path('comment/<int:pk>/pin/',   views.PinCommentView.as_view()),
    path('comment/<int:pk>/flag/',  views.FlagCommentView.as_view()),
]
