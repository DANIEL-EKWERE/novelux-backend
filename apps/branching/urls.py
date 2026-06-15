from django.urls import path
from . import views

urlpatterns = [
    path('<slug:story_slug>/chapters/<int:chapter_number>/branches/',
         views.ChapterBranchPointsView.as_view()),
    path('vote/<int:branch_point_id>/',
         views.CastVoteView.as_view()),
    path('results/<int:branch_point_id>/',
         views.BranchPointResultsView.as_view()),
]
