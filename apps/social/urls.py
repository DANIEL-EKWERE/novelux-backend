from django.urls import path

from . import views

urlpatterns = [
    path('overview/',                          views.overview),
    path('settings/',                          views.update_settings),
    path('accounts/',                          views.accounts),
    path('accounts/<int:pk>/',                 views.account_detail),
    path('accounts/<int:pk>/test/',            views.account_test),
    path('books/',                             views.books),
    path('posts/',                             views.posts),
    path('posts/<int:pk>/',                    views.post_detail),
    path('posts/<int:pk>/<str:action>/',       views.post_action),
    path('analytics/',                         views.analytics),
    path('sync/',                              views.sync_now),
    path('inbox/',                             views.inbox),
    path('inbox/<int:pk>/reply/',              views.inbox_reply),
    path('inbox/<int:pk>/handled/',            views.inbox_handled),
]
