from django.urls import path
from . import views

urlpatterns = [
    path('',                            views.StoryListCreateView.as_view()),
    path('mine/',                       views.MyStoriesView.as_view()),
    path('trending/',                   views.TrendingStoriesView.as_view()),
    path('featured/',                   views.FeaturedStoriesView.as_view()),
    path('editors-pick/',               views.EditorsPickView.as_view()),
    path('completed-stories/',          views.CompletedStoriesView.as_view()),
    path('free-download/',              views.FreeDownloadStoriesView.as_view()),
    path('world-Famous/',               views.WorldFamousStoriesView.as_view()),
    path('african-folktale/',           views.AfricanFolktaleStoriesView.as_view()),
    path('bookmarks/',                  views.MyBookmarksView.as_view()),
    path('genres/',                     views.GenreListView.as_view()),
    path('tags/',                       views.TagListView.as_view()),
    path('banners/', views.PromoBannersView.as_view(), name='promo-banners'),
    path('request/', views.BookRequestView.as_view(), name='book-request'),
    path('<slug:slug>/',                views.StoryDetailView.as_view()),
    path('<slug:slug>/bookmark/',       views.BookmarkView.as_view()),
    path('<slug:slug>/progress/',       views.UpdateReadingProgressView.as_view()),
    path('<slug:slug>/rate/',           views.RateStoryView.as_view()),
    path('<slug:slug>/apply-contract/',   views.apply_for_contract),
]