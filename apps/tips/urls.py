from django.urls import path
from . import views

urlpatterns = [
    path('<slug:story_slug>/tip/',          views.SendTipView.as_view()),
    path('<slug:story_slug>/top-tippers/',  views.StoryTopTippersView.as_view()),
    path('sent/',                           views.MyTipsSentView.as_view()),
    path('received/',                       views.MyTipsReceivedView.as_view()),
    path('<slug:slug>/top-tippers/', views.TopTippersView.as_view(), name='top-tippers'),
]
