from django.urls import path
from .views import (
    ReadingSessionView,
    ReadingStatsView,
    ReadingScheduleView,
    ReadingHistoryView,
)

urlpatterns = [
    path('session/',   ReadingSessionView.as_view()),
    path('stats/',     ReadingStatsView.as_view()),
    path('schedule/',  ReadingScheduleView.as_view()),
    path('history/',   ReadingHistoryView.as_view(),       name='reading-history'),
]