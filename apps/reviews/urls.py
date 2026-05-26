from django.urls import path
from .views import ReportView, StoryReviewsView, ReviewLikeView, ReportMissingStoryView

urlpatterns = [
    path("report/", ReportView.as_view(), name="story-reviews"),
    path("report-missing-story/", ReportMissingStoryView.as_view(), name="report-missing-story"),

    path('<slug:slug>/reviews/',
         StoryReviewsView.as_view(),
         name='story-reviews'),

    path('<slug:slug>/reviews/<int:review_id>/like/',
         ReviewLikeView.as_view(),
         name='review-like'),
]