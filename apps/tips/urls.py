from django.urls import path
from . import views

urlpatterns = [
    path('<slug:story_slug>/tip/',          views.SendTipView.as_view()),
    path('<slug:story_slug>/gift/',         views.GiftIntentView.as_view()),
    path('gift/<int:pk>/confirm/',          views.GiftConfirmView.as_view()),
    path('<slug:story_slug>/top-tippers/',  views.StoryTopTippersView.as_view(), name='top-tippers'),
    path('sent/',                           views.MyTipsSentView.as_view()),
    path('received/',                       views.MyTipsReceivedView.as_view()),
]
